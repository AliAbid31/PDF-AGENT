"use client";

import { useState, useRef, useEffect } from "react";
import {
  Plus,
  Send,
  FileText,
  LogOut,
  Menu,
  X,
  Briefcase,
  BookOpen,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { ThemeToggle } from "../components/theme-toggle";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
}

interface User {
  id: string;
  email: string;
}

export function Dashboard() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] =
    useState<Conversation | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [uploadedFile, setUploadedFile] = useState<
    { file: File; name: string; size: number } | null
  >(null);
  const [uploading, setUploading] = useState(false);
  const [requestError, setRequestError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) {
          router.push("/login");
          return;
        }
  
        const response = await fetch("/api/auth/me", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
  
        if (!response.ok) {
          // For testing, use mock user if backend is unavailable
          setUser({
            id: "test-user-123",
            email: "user@alipdf.com",
          });
          return;
        }
  
        const userData = await response.json();
        setUser(userData);
      } catch (error) {
        console.error("Failed to fetch user:", error);
        // For testing, use mock user if backend connection fails
        setUser({
          id: "test-user-123",
          email: "user@alipdf.com",
        });
      }
    };
    fetchUser();
  }, [router]);
  

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentConversation?.messages]);

  const handleSendMessage = async () => {
    const messageContent = input.trim();
    if (!messageContent || loading || uploading) return;

    const newMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: messageContent,
      timestamp: new Date(Date.now()),
    };

    setInput("");
    setLoading(true);
    setRequestError("");

    if (currentConversation) {
      setCurrentConversation((prev) =>
        prev
          ? { ...prev, messages: [...prev.messages, newMessage] }
          : null
      );
    } else {
      const newConversation: Conversation = {
        id: Date.now().toString(),
        title: messageContent.slice(0, 40),
        messages: [newMessage],
        createdAt: new Date(Date.now()),
      };
      setConversations((prev) => [newConversation, ...prev]);
      setCurrentConversation(newConversation);
    }

    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        throw new Error("Your session has expired. Please sign in again.");
      }

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: messageContent }),
      });

      if (!response.ok || !response.body) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "The assistant could not answer.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantContent = "";
      let buffer = "";

      const appendAssistantMessage = (content: string) => {
        setCurrentConversation((prev) => {
          if (!prev) return prev;
          const lastMessage = prev.messages[prev.messages.length - 1];
          if (lastMessage?.role === "assistant") {
            return {
              ...prev,
              messages: [
                ...prev.messages.slice(0, -1),
                { ...lastMessage, content },
              ],
            };
          }
          return {
            ...prev,
            messages: [
              ...prev.messages,
              {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content,
                timestamp: new Date(),
              },
            ],
          };
        });
      };

      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          const eventType =
            event
              .split("\n")
              .find((line) => line.startsWith("event:"))
              ?.slice(6)
              .trim() || "message";
          const content = event
            .split("\n")
            .filter((line) => line.startsWith("data:"))
            .map((line) => line.slice(5).trimStart())
            .join("\n");
          if (content) {
            if (eventType === "error") {
              throw new Error(content);
            }
            assistantContent += content;
            appendAssistantMessage(assistantContent);
          }
        }

        if (done) break;
      }

      if (!assistantContent) {
        throw new Error("The assistant returned an empty response.");
      }
    } catch (error) {
      setRequestError(
        error instanceof Error ? error.message : "The request failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== "application/pdf") {
      setRequestError("Only PDF files are allowed.");
      return;
    }

    setUploading(true);
    setRequestError("");
    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        throw new Error("Your session has expired. Please sign in again.");
      }

      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("/api/documents/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "The PDF could not be uploaded.");
      }

      setUploadedFile({ file, name: file.name, size: file.size });
    } catch (error) {
      setRequestError(
        error instanceof Error ? error.message : "The PDF upload failed.",
      );
    } finally {
      setUploading(false);
    }
  };

  const handleNewChat = () => {
    const newConversation: Conversation = {
      id: Date.now().toString(),
      title: "New Conversation",
      messages: [],
      createdAt: new Date(Date.now()),
    };
    setConversations((prev) => [newConversation, ...prev]);
    setCurrentConversation(newConversation);
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.push("/login");
  };

  return (
    <div className="h-screen flex bg-white dark:bg-slate-950 overflow-hidden">
      <ThemeToggle />

      {/* Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ x: -300 }}
            animate={{ x: 0 }}
            exit={{ x: -300 }}
            transition={{ duration: 0.3 }}
            className="w-64 bg-gradient-to-b from-slate-50 dark:from-slate-900 to-white dark:to-slate-950 border-r border-slate-200 dark:border-slate-800 flex flex-col"
          >
            {/* Header */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2 mb-6">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500 to-pink-600 dark:from-blue-500 dark:to-purple-600 flex items-center justify-center text-white">
                  <FileText className="w-4 h-4" />
                </div>
                <h1 className="font-bold text-slate-900 dark:text-white">
                  ali-pdf.ai
                </h1>
              </div>
              <button
                onClick={handleNewChat}
                className="w-full py-2 px-3 bg-red-500 dark:bg-blue-600 hover:bg-red-600 dark:hover:bg-blue-700 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors text-sm"
              >
                <Plus className="w-4 h-4" />
                New Chat
              </button>
            </div>

            {/* Workspace & PDF Library */}
            <div className="p-4 space-y-3 border-b border-slate-200 dark:border-slate-800">
              <button className="w-full flex items-center gap-3 px-3 py-2 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors text-sm">
                <Briefcase className="w-4 h-4" />
                <span>Workspace</span>
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors text-sm">
                <BookOpen className="w-4 h-4" />
                <span>PDF Library</span>
              </button>
            </div>

            {/* Conversations */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {conversations.length === 0 ? (
                <p className="text-xs text-slate-500 dark:text-slate-400 p-3 text-center">
                  No conversations yet
                </p>
              ) : (
                conversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    onClick={() => setCurrentConversation(conversation)}
                    className={`w-full text-left p-3 rounded-lg transition-all text-sm ${
                      currentConversation?.id === conversation.id
                        ? "bg-red-500/20 dark:bg-blue-500/20 text-red-600 dark:text-blue-400 border border-red-500/50 dark:border-blue-500/50"
                        : "text-slate-700 dark:text-slate-300 hover:bg-slate-200/50 dark:hover:bg-slate-800/50"
                    }`}
                  >
                    <p className="font-medium truncate">
                      {conversation.title}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      {conversation.messages.length} messages
                    </p>
                  </button>
                ))
              )}
            </div>

            {/* Bottom */}
            <div className="border-t border-slate-200 dark:border-slate-800 p-4 space-y-2">
              {user && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-slate-100 dark:bg-slate-800">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-red-500 to-pink-600 dark:from-blue-500 dark:to-purple-600 flex-shrink-0"></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-900 dark:text-white truncate">
                      {user.email.split("@")[0]}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                      {user.email}
                    </p>
                  </div>
                </div>
              )}
              <button
                onClick={handleLogout}
                className="w-full py-2 px-3 text-red-600 dark:text-red-400 hover:bg-red-500/10 dark:hover:bg-red-500/10 rounded-lg flex items-center gap-2 transition-colors text-sm font-medium"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                <Menu className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              </button>
            )}
            {sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(false)}
                className="hidden sm:block p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              </button>
            )}
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-white">
                {currentConversation?.title || "New Chat"}
              </h2>
              {currentConversation?.messages.length === 0 && (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Start a conversation
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {!currentConversation ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="h-full flex flex-col items-center justify-center gap-8"
            >
              <div className="text-center max-w-md">
                <h3 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">
                  Hello, how can I assist you today?
                </h3>
                <p className="text-slate-600 dark:text-slate-400">
                  Start a new chat to begin
                </p>
              </div>
            </motion.div>
          ) : currentConversation.messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="h-full flex flex-col items-center justify-center gap-8"
            >
              <div className="text-center max-w-md">
                <h3 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">
                  Hello, how can I assist you today?
                </h3>
                <p className="text-slate-600 dark:text-slate-400">
                  Start by uploading a PDF or asking a question about your
                  documents
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
                <button className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-left transition-colors">
                  <p className="font-medium text-slate-900 dark:text-white text-sm">
                    📊 Summarize a 50-page PDF
                  </p>
                </button>
                <button className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-left transition-colors">
                  <p className="font-medium text-slate-900 dark:text-white text-sm">
                    📄 Draft an executive report
                  </p>
                </button>
                <button className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-left transition-colors">
                  <p className="font-medium text-slate-900 dark:text-white text-sm">
                    💰 Extract key financial metrics
                  </p>
                </button>
                <button className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-left transition-colors">
                  <p className="font-medium text-slate-900 dark:text-white text-sm">
                    🔍 Find specific clauses
                  </p>
                </button>
              </div>
            </motion.div>
          ) : (
            <div className="space-y-4">
              {currentConversation.messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-4 ${
                    message.role === "user" ? "justify-end" : ""
                  }`}
                >
                  {message.role === "assistant" && (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-red-500 to-pink-600 dark:from-blue-500 dark:to-purple-600 flex-shrink-0 flex items-center justify-center text-white text-sm font-bold">
                      A
                    </div>
                  )}
                  <div
                    className={`max-w-xl px-4 py-3 rounded-lg ${
                      message.role === "user"
                        ? "bg-red-500 dark:bg-blue-600 text-white rounded-br-none"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white rounded-bl-none"
                    }`}
                  >
                    <p className="text-sm">{message.content}</p>
                    <p
                      className={`text-xs mt-2 ${
                        message.role === "user"
                          ? "text-blue-100 dark:text-blue-200"
                          : "text-slate-500 dark:text-slate-400"
                      }`}
                    >
                      {message.timestamp.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </motion.div>
              ))}
              {loading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-4"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-red-500 to-pink-600 dark:from-blue-500 dark:to-purple-600 flex-shrink-0 flex items-center justify-center text-white text-sm font-bold">
                    A
                  </div>
                  <div className="bg-slate-100 dark:bg-slate-800 px-4 py-3 rounded-lg rounded-bl-none">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce"></div>
                      <div
                        className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce"
                        style={{ animationDelay: "0.2s" }}
                      ></div>
                      <div
                        className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce"
                        style={{ animationDelay: "0.4s" }}
                      ></div>
                    </div>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 p-4">
          {requestError && (
            <div className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300">
              {requestError}
            </div>
          )}

          {uploadedFile && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-3 p-3 bg-red-50 dark:bg-blue-900/20 border border-red-200 dark:border-blue-800 rounded-lg flex items-center justify-between text-sm"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-red-600 dark:text-blue-400" />
                <div>
                  <p className="font-medium text-red-900 dark:text-blue-100">
                    {uploadedFile.name}
                  </p>
                  <p className="text-xs text-red-700 dark:text-blue-200">
                    {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setUploadedFile(null);
                  setRequestError("");
                }}
                className="text-red-600 dark:text-blue-400 hover:text-red-700 dark:hover:text-blue-300"
                aria-label="Remove uploaded PDF"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          )}

          <div className="flex gap-3 items-end">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf"
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || loading}
              aria-label={uploading ? "Uploading PDF" : "Upload PDF"}
              className="p-3 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition-colors flex-shrink-0"
            >
              {uploading ? (
                <div className="w-5 h-5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
              ) : (
                <Plus className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              )}
            </button>

            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Ask anything about your documents, cite clauses, or synthesize data..."
              className="flex-1 px-4 py-3 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white placeholder-slate-500 dark:placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-red-500/50 dark:focus:ring-blue-500/50 resize-none max-h-32"
              rows={1}
            />

            <button
              onClick={handleSendMessage}
              disabled={!input.trim() || loading || uploading}
              aria-label={
                uploading
                  ? "Waiting for PDF upload"
                  : loading
                    ? "Sending message"
                    : "Send message"
              }
              className="p-3 bg-red-500 dark:bg-blue-600 hover:bg-red-600 dark:hover:bg-blue-700 disabled:bg-slate-400 dark:disabled:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-200 flex-shrink-0"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
