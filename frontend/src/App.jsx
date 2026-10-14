
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeftRight,
  ArrowUpRight,
  AudioLines,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Clock3,
  LayoutDashboard,
  Menu,
  Mic,
  MicOff,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Upload,
  Wallet,
  Search,
  ReceiptText,
  X,
  AlertCircle,
  FileAudio,
  RotateCcw,
  LockKeyhole,
  Settings2,
} from "lucide-react";
import "./index.css";
import VoxBankWelcome from "./components/VoxBankWelcome";

function createConversationId() {
  return typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `conversation-${Date.now()}`;
}

const APP_TIME_ZONE = "Asia/Kolkata";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const currentTime = () =>
  new Date().toLocaleTimeString("en-IN", {
    timeZone: APP_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
  });

const welcomeMessage = {
  id: "welcome",
  role: "assistant",
  text: "Hello! I’m your voice banking assistant. Try saying, “Pay five hundred rupees to Ravi Kumar.” I’ll ask you to review and confirm before completing the mock payment.",
  time: "Now",
};

function formatINR(amount) {
  const value = Number(amount);

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(value) ? value : 0);
}

function formatTransactionDate(value) {
  if (!value) return "Date unavailable";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : date.toLocaleString("en-IN", {
        timeZone: APP_TIME_ZONE,
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}

function formatStatus(value) {
  return String(value || "unknown").replaceAll("_", " ");
}

function getErrorMessage(detail, status) {
  const message =
    typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item.msg || "Invalid input").join(". ")
        : "";

  const normalized = message.toLowerCase();

  if (
    normalized.includes("maximum transaction") ||
    normalized.includes("transaction limit") ||
    normalized.includes("exceeds") ||
    normalized.includes("daily transfer limit")
  ) {
    return message;
  }

  if (normalized.includes("unsupported audio format")) {
    return "This audio format is not supported. Try WAV, MP3, M4A, or WebM audio.";
  }

  if (status === 413) {
    return "The audio file is too large. Please choose a shorter recording.";
  }

  if (status === 422) {
    return "The request could not be validated. Please try again.";
  }

  if (status >= 500) {
    return "The banking service encountered an error. Please try again.";
  }

  return message || `Request failed with status ${status}.`;
}

function StatusBadge({ status }) {
  const normalized = String(status || "unknown")
    .toLowerCase()
    .replaceAll("_", "-");

  return (
    <span className={`status-badge status-${normalized}`}>
      <span className="badge-dot" />
      {formatStatus(status)}
    </span>
  );
}

function EmptyState({ icon: Icon = Wallet, title, children }) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon size={22} />
      </span>
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}

export default function App() {
  const [conversationId, setConversationId] = useState(createConversationId);
  const [messages, setMessages] = useState([welcomeMessage]);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [backendOnline, setBackendOnline] = useState(null);
  const [error, setError] = useState("");
  const [lastTranscript, setLastTranscript] = useState("");
  const [voiceStatus, setVoiceStatus] = useState("Ready");
  const [showWelcome, setShowWelcome] = useState(true);

  const [transactions, setTransactions] = useState([]);
  const [completedTransfersTotal, setCompletedTransfersTotal] =
    useState("0.00");

  // Balance is managed inside the App component.
  const [currentBalance, setCurrentBalance] = useState("25000.00");
  const [balanceError, setBalanceError] = useState("");
  const [balanceLoading, setBalanceLoading] = useState(false);

  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyRefreshing, setHistoryRefreshing] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [pendingPayment, setPendingPayment] = useState(null);

  const [showHelp, setShowHelp] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeNav, setActiveNav] = useState("overview");
  const [currentPage, setCurrentPage] = useState("overview");
  const [transactionFilter, setTransactionFilter] = useState("all");
  const [transactionSearch, setTransactionSearch] = useState("");
  const [selectedAudioFile, setSelectedAudioFile] = useState(null);

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const fileRef = useRef(null);
  const bottomRef = useRef(null);
  const assistantRef = useRef(null);
  const transactionsRef = useRef(null);
  const limitsRef = useRef(null);
  const helpRef = useRef(null);
  const busyRef = useRef(false);

  const checkBackend = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      setBackendOnline(response.ok);
      return response.ok;
    } catch {
      setBackendOnline(false);
      return false;
    }
  }, []);



  // Fetch the authoritative balance from the backend ledger.
  const fetchCurrentBalance = useCallback(async () => {
    setBalanceLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/balance`);
      const data = await response.json().catch(() => ({}));
      console.log("Balance API response:", response.status, data);

      if (!response.ok) {
        throw new Error(
          getErrorMessage(data.detail || data.message, response.status)
        );
      }

      if (
        data.balance === undefined ||
        data.balance === null ||
        !Number.isFinite(Number(data.balance))
      ) {
        throw new Error("The balance API returned an invalid balance.");
      }

      setCurrentBalance(String(data.balance));
      setBalanceError("");
      setBackendOnline(true);

      return true;
    } catch (err) {
      setBalanceError(err.message || "Unable to load the current balance.");
      console.error("Balance fetch failed:", err);

      return false;
    } finally {
      setBalanceLoading(false);
    }
  }, []);

  const fetchPaymentHistory = useCallback(
    async ({ quiet = false } = {}) => {
      if (!quiet) setHistoryLoading(true);

      setHistoryRefreshing(quiet);
      setHistoryError("");

      try {
        const response = await fetch(`${API_BASE_URL}/payments`);
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
          throw new Error(
            getErrorMessage(data.detail, response.status)
          );
        }

        const rows = Array.isArray(data.transactions)
          ? data.transactions
          : [];

        setTransactions(rows);
        setCompletedTransfersTotal(
          data.completed_transfers_total ?? "0.00"
        );
        setBackendOnline(true);

        return rows;
      } catch (err) {
        setHistoryError(
          err.message ||
            "Transaction history is temporarily unavailable."
        );

        return null;
      } finally {
        setHistoryLoading(false);
        setHistoryRefreshing(false);
      }
    },
    []
  );

  // Load backend status, payment history and balance when the app opens.
  useEffect(() => {
    checkBackend();
    fetchPaymentHistory();
    fetchCurrentBalance();

    return () =>
      streamRef.current?.getTracks().forEach((track) => track.stop());
  }, [checkBackend, fetchPaymentHistory, fetchCurrentBalance]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, busy]);

  useEffect(() => {
    if (currentPage === "transactions") {
      window.scrollTo({ top: 0, behavior: "smooth" });
      fetchPaymentHistory({ quiet: true });
      return;
    }

    if (activeNav === "overview") {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    const target =
      activeNav === "assistant"
        ? assistantRef.current
        : activeNav === "limits"
          ? limitsRef.current
          : activeNav === "help"
            ? helpRef.current
            : null;

    target?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, [currentPage, activeNav, fetchPaymentHistory]);

  function addMessage(role, text, extra = {}) {
    setMessages((previous) => [
      ...previous,
      {
        id: `${Date.now()}-${Math.random()}`,
        role,
        text,
        time: currentTime(),
        ...extra,
      },
    ]);
  }

  function resetConversation() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    busyRef.current = false;

    setConversationId(createConversationId());
    setMessages([welcomeMessage]);
    setRecording(false);
    setBusy(false);
    setError("");
    setLastTranscript("");
    setVoiceStatus("Ready");
    setPendingPayment(null);
    setSelectedAudioFile(null);
  }

  async function sendAudio(blob, filename) {
    if (busyRef.current || paymentBusy) return;

    if (!blob || blob.size === 0) {
      const message = "No audio was recorded. Please try again.";
      setError(message);
      addMessage("assistant", message, { kind: "error" });
      return;
    }

    busyRef.current = true;
    setBusy(true);
    setError("");
    setVoiceStatus("Processing");

    addMessage("user", "Voice message sent", {
        kind: "audio",
        });

    const formData = new FormData();
    formData.append("conversation_id", conversationId);
    formData.append("file", blob, filename);

    try {
      const response = await fetch(`${API_BASE_URL}/voice`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          getErrorMessage(data.detail || data.message, response.status)
        );
      }

      setBackendOnline(true);

      const transcript =
        typeof data.transcribed_text === "string"
          ? data.transcribed_text.replace(/\s+/g, " ").trim()
          : "";

      if (transcript) {
        setLastTranscript(transcript);

        addMessage("user", transcript, {
          kind: "transcript",
        });
      }

      const result = data.conversation || data;
      const status = result.status || data.status || "processed";
      const message =
        result.message || data.message || "Your request was processed.";

      const finalStatus = String(status).toLowerCase();
      const paymentFinished =
        ["completed", "cancelled", "canceled"].includes(finalStatus) ||
        /mock payment completed|payment cancelled|payment canceled/i.test(message);

      if (paymentFinished) {
        setLastTranscript("");
      }

      addMessage("assistant", message, { status });

      // Speak the assistant's response aloud.
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(message);
        utterance.lang = "en-IN";
        utterance.rate = 0.95;

        window.speechSynthesis.speak(utterance);
      }

      setVoiceStatus(
        status === "awaiting_confirmation"
          ? "Awaiting confirmation"
          : status === "completed"
            ? "Completed"
            : status === "cancelled"
              ? "Cancelled"
              : status === "error"
                ? "Error"
                : "Ready"
      );

      if (Array.isArray(data.registered_payees)) {
        addMessage(
          "assistant",
          `Registered recipients: ${data.registered_payees.join(", ")}. Please say the recipient’s name again.`,
          { kind: "hint" }
        );
      }

      const rows = await fetchPaymentHistory({ quiet: true });

      if (status === "awaiting_confirmation" && rows) {
        const pending = rows.find(
          (item) => String(item.status).toLowerCase() === "pending"
        );

        if (pending) setPendingPayment(pending);
      } else if (status === "completed" || status === "cancelled") {
        setPendingPayment(null);
      }

      // Also refresh the balance in case the backend completed a payment
      // as part of processing this request.
      if (status === "completed") {
        await fetchCurrentBalance();
      }
    } catch (err) {
      const message = err.message || "Could not process your request.";

      const connectionError =
        err instanceof TypeError ||
        /failed to fetch|networkerror/i.test(message);

      const friendly = connectionError
        ? "Cannot connect to the banking service. Check that FastAPI is running on port 8000."
        : message;

      if (connectionError) setBackendOnline(false);

      setError(friendly);
      setVoiceStatus("Error");
      addMessage("assistant", friendly, { kind: "error" });
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  async function startRecording() {
    if (busyRef.current || paymentBusy || recording) return;

    setError("");

    if (
      !navigator.mediaDevices?.getUserMedia ||
      !window.MediaRecorder
    ) {
      setError(
        "This browser does not support microphone recording. Try a recent version of Chrome or upload an audio file."
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      streamRef.current = stream;
      chunksRef.current = [];

      const supportedType = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
      ].find((type) => MediaRecorder.isTypeSupported(type));

      const recorder = supportedType
        ? new MediaRecorder(stream, { mimeType: supportedType })
        : new MediaRecorder(stream);

      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onerror = () => {
        setError(
          "Recording failed. Please try again or upload an audio file."
        );
        setRecording(false);
        setVoiceStatus("Error");
      };

      recorder.onstop = async () => {
        const type = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type });
        const extension = type.includes("mp4") ? "m4a" : "webm";

        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        setRecording(false);

        await sendAudio(blob, `voice-message.${extension}`);
      };

      recorder.start();
      setRecording(true);
      setVoiceStatus("Listening");
    } catch (err) {
      setError(
        err.name === "NotAllowedError"
          ? "Microphone access was denied. Allow microphone permission in your browser settings, or upload an audio file instead."
          : "Couldn’t access your microphone. Check device permissions or upload an audio file."
      );

      setVoiceStatus("Error");
    }
  }

  function stopRecording() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }
  }

  function handleMicrophone() {
    if (busyRef.current || paymentBusy) return;

    if (recording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];

    if (!file) return;

    const allowed =
      /\.(wav|mp3|m4a|mp4|webm|mpeg|ogg|oga|aac|flac)$/i.test(
        file.name
      ) || /^audio\//i.test(file.type);

    if (!allowed) {
      setError(
        "Choose a supported audio file such as WAV, MP3, M4A, or WebM."
      );
      event.target.value = "";
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setError("Please choose an audio file smaller than 20 MB.");
      event.target.value = "";
      return;
    }

    setSelectedAudioFile(file);
    setError("");
    event.target.value = "";
  }

  async function handlePaymentDecision(
    confirmed,
    payment = pendingPayment
  ) {
    if (!payment?.payment_id || paymentBusy) return;

    setPaymentBusy(true);
    setError("");
    setVoiceStatus(
      confirmed ? "Processing" : "Processing cancellation"
    );

    try {
      const response = await fetch(
          `${API_BASE_URL}/payments/${encodeURIComponent(payment.payment_id)}/confirm`,
          {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmed }),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          getErrorMessage(data.detail || data.message, response.status)
        );
      }

      const status = String(data.status || "").toLowerCase();

      if (confirmed && status !== "completed") {
        throw new Error(
          "The backend did not confirm payment completion. Please refresh the transaction list to verify its current status."
        );
      }

      if (!confirmed && status !== "cancelled") {
        throw new Error(
          "The backend did not confirm cancellation. Please refresh the transaction list to verify its current status."
        );
      }

      const text =
        data.message ||
        (confirmed ? "Mock payment completed." : "Payment cancelled.");

      addMessage(
        "assistant",
        `${text}${data.payment_id ? ` Reference: ${data.payment_id}` : ""}`,
        {
          status,
          kind: confirmed ? "success" : "cancelled",
        }
      );

      setVoiceStatus(confirmed ? "Completed" : "Cancelled");

      setPendingPayment((current) =>
        current?.payment_id === payment.payment_id ? null : current
      );

      // Direct confirmation bypasses the voice conversation state.
      setConversationId(createConversationId());

      // Reload both resources after a successful decision.
      const [, balanceUpdated] = await Promise.all([
        fetchPaymentHistory({ quiet: true }),
        fetchCurrentBalance(),
      ]);

      if (!balanceUpdated) {
        setBalanceError(
          "Payment was updated, but the balance could not be refreshed. Use the refresh button to try again."
        );
      }
    } catch (err) {
      const message =
        err.message || "Could not update this payment. Please try again.";

      setError(message);

      if (currentPage === "transactions") {
        setHistoryError(message);
      }

      setVoiceStatus("Error");

      // If the confirmation request failed, refresh the data to reconcile
      // the UI with the actual backend state.
      await Promise.all([
        fetchPaymentHistory({ quiet: true }),
        fetchCurrentBalance(),
      ]);
    } finally {
      setPaymentBusy(false);
    }
  }

  function goTo(_ref, nav) {
    setActiveNav(nav);
    setMobileMenuOpen(false);

    if (nav === "help") setShowHelp(true);

    if (nav === "transactions") {
      setCurrentPage("transactions");
      return;
    }

    setCurrentPage("overview");

    if (nav === "overview") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  const latestPayment = transactions[0] || null;

  const normalizedTransactionStatus = (transaction) =>
    String(transaction.status || "unknown")
      .toLowerCase()
      .replaceAll(" ", "_")
      .replaceAll("-", "_");

  const filteredTransactions = transactions.filter((transaction) => {
    const status = normalizedTransactionStatus(transaction);

    const matchesFilter =
      transactionFilter === "all" ||
      (transactionFilter === "completed" && status === "completed") ||
      (transactionFilter === "pending" &&
        [
          "pending",
          "pending_confirmation",
          "awaiting_confirmation",
        ].includes(status)) ||
      (transactionFilter === "failed" &&
        ["failed", "error"].includes(status)) ||
      (transactionFilter === "cancelled" && status === "cancelled");

    const query = transactionSearch.trim().toLowerCase();

    const matchesSearch =
      !query ||
      `${transaction.payee_name || ""} ${transaction.payment_id || ""} ${transaction.status || ""}`
        .toLowerCase()
        .includes(query);

    return matchesFilter && matchesSearch;
  });

  const backendLabel =
    backendOnline === null
      ? "Connecting"
      : backendOnline
        ? "Connected"
        : "Offline";



  return (

    <div className="app-shell">
      {mobileMenuOpen && (
        <button
          className="drawer-backdrop"
          aria-label="Close navigation menu"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <aside
        className={`sidebar ${mobileMenuOpen ? "sidebar-open" : ""}`}
        aria-label="Main navigation"
      >
        {showWelcome && (
  <VoxBankWelcome
    onContinue={() => setShowWelcome(false)}
  />
)}
        <a
          className="brand"
          href="#overview"
          onClick={() => {
            setActiveNav("overview");
            setCurrentPage("overview");
            setMobileMenuOpen(false);
          }}
        >
          <span className="brand-icon">
            <AudioLines size={22} />
          </span>

          <span className="brand-copy">
            <strong>
              Vox<span>Bank</span>
            </strong>
            <small>VOICE BANKING</small>
          </span>

          <button
            className="drawer-close"
            aria-label="Close navigation"
            onClick={(event) => {
              event.preventDefault();
              setMobileMenuOpen(false);
            }}
          >
            <X size={18} />
          </button>
        </a>

        <div className="sidebar-section-label">WORKSPACE</div>

        <nav className="navigation">
          <button
            className={`nav-item ${activeNav === "overview" ? "active" : ""}`}
            onClick={() => goTo(null, "overview")}
          >
            <LayoutDashboard size={18} />
            <span>Overview</span>
          </button>

          <button
            className={`nav-item ${activeNav === "assistant" ? "active" : ""}`}
            onClick={() => goTo(assistantRef, "assistant")}
          >
            <AudioLines size={18} />
            <span>Voice assistant</span>
          </button>

          <button
            className={`nav-item ${activeNav === "transactions" ? "active" : ""}`}
            onClick={() => goTo(null, "transactions")}
          >
            <ArrowLeftRight size={18} />
            <span>Transactions</span>
          </button>

          <button
            className={`nav-item ${activeNav === "limits" ? "active" : ""}`}
            onClick={() => goTo(limitsRef, "limits")}
          >
            <ShieldCheck size={18} />
            <span>Security &amp; limits</span>
          </button>

          <button
            className={`nav-item ${activeNav === "help" ? "active" : ""}`}
            onClick={() => goTo(helpRef, "help")}
          >
            <CircleHelp size={18} />
            <span>Help &amp; support</span>
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="security-card">
            <span className="security-icon">
              <LockKeyhole size={17} />
            </span>
            <div>
              <strong>Demo environment</strong>
              <small>No real money moves</small>
            </div>
          </div>

          <div className="sidebar-connection">
            <span
              className={`status-dot ${
                backendOnline === true
                  ? "online"
                  : backendOnline === false
                    ? "offline"
                    : ""
              }`}
            />
            <span>Backend {backendLabel}</span>
            <button
              onClick={checkBackend}
              aria-label="Refresh backend status"
            >
              <RefreshCw size={14} />
            </button>
          </div>

          <div className="profile">
            <div className="profile-avatar">C</div>
            <div className="profile-copy">
              <strong>Customer</strong>
              <small>Demo account</small>
            </div>
            <span className="profile-more">
              <Settings2 size={16} />
            </span>
          </div>
        </div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="mobile-menu-button"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              <Menu size={21} />
            </button>

            <div>
              <div className="breadcrumb">
                Workspace <span>/</span>{" "}
                <strong>
                  {currentPage === "transactions"
                    ? "Transactions"
                    : activeNav === "assistant"
                      ? "Voice assistant"
                      : activeNav === "limits"
                        ? "Security & limits"
                        : activeNav === "help"
                          ? "Help & support"
                          : "Overview"}
                </strong>
              </div>

              <h2 className="topbar-title">
                {currentPage === "transactions"
                  ? "Transaction History"
                  : "Your Banking Overview"}
              </h2>
            </div>
          </div>

          <div className="topbar-right">
            <div className="date-label">
              <Clock3 size={15} />
              {new Date().toLocaleDateString("en-IN", {
                timeZone: APP_TIME_ZONE,
                weekday: "short",
                day: "numeric",
                month: "short",
                year: "numeric",
              })}
            </div>

            <span
              className={`connection-pill ${
                backendOnline === false
                  ? "is-offline"
                  : backendOnline === null
                    ? "is-checking"
                    : ""
              }`}
            >
              <span
                className={`status-dot ${
                  backendOnline === true
                    ? "online"
                    : backendOnline === false
                      ? "offline"
                      : ""
                }`}
              />
              {backendLabel}
            </span>

            <button
              className="help-icon-button"
              aria-label="Open help"
              onClick={() => {
                setShowHelp(true);
                goTo(helpRef, "help");
              }}
            >
              <CircleHelp size={19} />
            </button>
          </div>
        </header>

        <div className="page-content">
          {currentPage === "overview" && (
            <>
              <section className="welcome-row">
                <div>
                  <div className="eyebrow">
                    <Sparkles size={14} />
                    YOUR BANKING, YOUR VOICE
                  </div>

                  <h1>
                    Banking, made conversational<span>.</span>
                  </h1>

                  <p className="subtitle">
                    Manage your mock payments using natural voice conversations.
                  </p>
                </div>

                <button
                  className="primary-button new-conversation"
                  onClick={() => {
                    resetConversation();
                    goTo(assistantRef, "assistant");
                  }}
                >
                  <Plus size={17} />
                  Start a conversation
                </button>
              </section>

              <section className="stats-grid" aria-label="Account summary">
                <article className="stat-card">
                  <div className="stat-card-top">
                    <span className="stat-icon purple">
                      <Wallet size={19} />
                    </span>
                    <span className="stat-caption">DEMO BALANCE</span>
                  </div>

                  <strong className="stat-value">
                    {balanceLoading
                      ? "Loading…"
                      : formatINR(currentBalance)}
                  </strong>

                  <div className="stat-footer">
                    <span
                      className={`pill ${
                        balanceError ? "" : "green-pill"
                      }`}
                    >
                      {balanceError ? "Unavailable" : "Ledger-based"}
                    </span>

                    <span>
                      {balanceError
                        ? "Could not refresh balance"
                        : "Simulated demo balance"}
                    </span>

                    <button
                      className="icon-button"
                      onClick={fetchCurrentBalance}
                      disabled={balanceLoading}
                      aria-label="Refresh account balance"
                      title="Refresh balance"
                    >
                      <RefreshCw
                        size={14}
                        className={balanceLoading ? "spin" : ""}
                      />
                    </button>
                  </div>

                  {balanceError && (
                    <p className="transaction-error" role="alert">
                      {balanceError}
                    </p>
                  )}
                </article>

                <article className="stat-card">
                  <div className="stat-card-top">
                    <span className="stat-icon blue">
                      <ArrowUpRight size={19} />
                    </span>
                    <span className="stat-caption">
                      COMPLETED TRANSFERS
                    </span>
                  </div>

                  <strong className="stat-value">
                    {formatINR(completedTransfersTotal)}
                  </strong>

                  <div className="stat-footer">
                    Backend-reported completed total
                  </div>
                </article>

                <article className="stat-card">
                  <div className="stat-card-top">
                    <span className="stat-icon amber">
                      <Clock3 size={19} />
                    </span>
                    <span className="stat-caption">LAST PAYMENT</span>
                  </div>

                  {latestPayment ? (
                    <>
                      <strong className="stat-value stat-value-small">
                        {latestPayment.payee_name || "Recipient"}
                      </strong>
                      <div className="stat-footer">
                        <strong>{formatINR(latestPayment.amount)}</strong>
                        <StatusBadge status={latestPayment.status} />
                      </div>
                    </>
                  ) : (
                    <>
                      <strong className="stat-value stat-value-small">
                        No payments yet
                      </strong>
                      <div className="stat-footer">
                        Your latest payment will appear here
                      </div>
                    </>
                  )}
                </article>

                <article className="stat-card">
                  <div className="stat-card-top">
                    <span className="stat-icon lavender">
                      <AudioLines size={19} />
                    </span>
                    <span className="stat-caption">ASSISTANT STATUS</span>
                  </div>

                  <strong className="stat-value stat-value-small status-text">
                    {voiceStatus}
                  </strong>

                  <div className="stat-footer">
                    <span
                      className={`status-dot ${
                        voiceStatus === "Error"
                          ? "offline"
                          : voiceStatus === "Listening"
                            ? "online recording-dot"
                            : ""
                      }`}
                    />
                    {recording
                      ? "Microphone is actively recording"
                      : pendingPayment
                        ? "Review the pending payment below"
                        : "You stay in control of every transfer"}
                  </div>
                </article>
              </section>

              <section className="workspace-grid">
                <section className="conversation-card" ref={assistantRef}>
                  <header className="conversation-header">
                    <div className="assistant-profile">
                      <div className="assistant-icon">
                        <AudioLines size={21} />
                      </div>
                      <div>
                        <h2>Voice Banking Assistant</h2>
                        <p>
                          <span
                            className={`status-dot ${
                              backendOnline === false ? "offline" : "online"
                            }`}
                          />
                          Speak naturally. Review every payment before confirming.
                        </p>
                      </div>
                    </div>

                    <button
                      className="icon-button"
                      onClick={resetConversation}
                      aria-label="Reset conversation"
                    >
                      <RotateCcw size={17} />
                    </button>
                  </header>

                  <div className="session-bar">
                    <span><i /> LIVE SESSION</span>
                    <span>Conversation · {conversationId.slice(0, 8)}</span>
                  </div>

                  <div
                    className="chat-list"
                    aria-live="polite"
                    aria-relevant="additions text"
                  >
                    {messages.length === 1 && (
                      <div className="suggested-prompts">
                        <span className="suggested-label">TRY ASKING</span>

                        <button
                          onClick={() =>
                            addMessage(
                              "assistant",
                              "To make a payment, tap the microphone and say: ‘Pay five hundred rupees to Ravi Kumar.’ I’ll ask you to review it before confirming.",
                              { kind: "hint" }
                            )
                          }
                        >
                          “I want to send ₹500 to Ravi.” <ChevronRight size={15} />
                        </button>

                        <button onClick={() => goTo(null, "transactions")}>
                          “Show my recent transactions.” <ChevronRight size={15} />
                        </button>

                        <button onClick={() => goTo(limitsRef, "limits")}>
                          “Help me understand transfer limits.” <ChevronRight size={15} />
                        </button>
                      </div>
                    )}

                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`message-row ${
                          message.role === "user" ? "user-row" : ""
                        }`}
                      >
                        {message.role === "assistant" && (
                          <div className="message-avatar">
                            <AudioLines size={15} />
                          </div>
                        )}

                        <div className="message-content">
                          <div className="message-meta">
                            <strong>
                              {message.role === "assistant"
                                ? "VoxBank assistant"
                                : "You"}
                            </strong>
                            <span>{message.time}</span>
                          </div>

                          <div
                            className={`message-bubble ${
                              message.kind === "error" ? "error-bubble" : ""
                            }`}
                          >
                            {message.kind === "audio" && <FileAudio size={15} />}
                            <span>{message.text}</span>
                          </div>

                          {message.status === "awaiting_confirmation" && (
                            <div className="message-hint">
                              <ShieldCheck size={14} />
                              Review the payment details below before confirming.
                            </div>
                          )}

                          {message.status === "completed" && (
                            <div className="message-success">
                              <CheckCircle2 size={14} />
                              Backend confirmed mock payment completion
                            </div>
                          )}
                        </div>

                        {message.role === "user" && (
                          <div className="user-avatar">YOU</div>
                        )}
                      </div>
                    ))}

                    {busy && (
                      <div className="processing" role="status">
                        <span />
                        <span />
                        <span />
                        Processing your request…
                      </div>
                    )}

                    <div ref={bottomRef} />
                  </div>

                  {pendingPayment && (
                    <section
                      className="payment-confirmation"
                      aria-labelledby="payment-confirm-title"
                    >
                      <div className="payment-confirm-top">
                        <span className="pending-icon">
                          <ShieldCheck size={19} />
                        </span>
                        <div>
                          <h3 id="payment-confirm-title">Review this payment</h3>
                          <p>Pending confirmation · Mock transaction only</p>
                        </div>
                        <StatusBadge status="pending" />
                      </div>

                      <div className="payment-detail-grid">
                        <div>
                          <span>Payee</span>
                          <strong>{pendingPayment.payee_name}</strong>
                        </div>
                        <div>
                          <span>Amount</span>
                          <strong className="payment-amount">
                            {formatINR(pendingPayment.amount)}
                          </strong>
                        </div>
                        <div className="payment-reference">
                          <span>Payment reference</span>
                          <strong>{pendingPayment.payment_id}</strong>
                        </div>
                      </div>

                      <p className="payment-warning">
                        <AlertCircle size={15} />
                        This is a simulated payment. Confirm only if the recipient
                        and amount are correct.
                      </p>

                      <div className="payment-actions">
                        <button
                          className="secondary-button cancel-payment"
                          disabled={paymentBusy}
                          onClick={() => handlePaymentDecision(false)}
                        >
                          <X size={16} />
                          {paymentBusy ? "Please wait…" : "Cancel payment"}
                        </button>

                        <button
                          className="primary-button confirm-payment"
                          disabled={paymentBusy}
                          onClick={() => handlePaymentDecision(true)}
                        >
                          {paymentBusy ? (
                            <RefreshCw className="spin" size={16} />
                          ) : (
                            <CheckCircle2 size={16} />
                          )}
                          {paymentBusy
                            ? "Processing…"
                            : "Confirm mock payment"}
                        </button>
                      </div>
                    </section>
                  )}

                  {showHelp && (
                    <div className="help-panel" ref={helpRef}>
                      <div>
                        <strong>How to use your assistant</strong>
                        <button
                          onClick={() => setShowHelp(false)}
                          aria-label="Close help"
                        >
                          <X size={15} />
                        </button>
                      </div>
                      <p><strong>1.</strong> Tap the microphone and say what you need.</p>
                      <p><strong>2.</strong> Review the recipient and amount before confirming.</p>
                      <p><strong>3.</strong> You can cancel any payment while it is pending.</p>
                      <p className="help-note">
                        If the backend is offline, start the FastAPI service and
                        retry. Audio upload is available if microphone access is
                        unavailable.
                      </p>
                    </div>
                  )}

                  {lastTranscript && (
                    <div className="transcript-panel">
                      <span>WHAT I HEARD</span>
                      <strong>{lastTranscript}</strong>
                      <p>
                        Please check the recipient and amount before confirming a transfer.
                      </p>
                    </div>
                  )}

                  {error && (
                    <div className="error-banner" role="alert">
                      <AlertCircle size={17} />
                      <span>{error}</span>
                      <button
                        onClick={() => setError("")}
                        aria-label="Dismiss error"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  )}

                  <div className="composer">
                    <div className="mic-row">
                      <button
                        className={`mic-button ${recording ? "recording" : ""}`}
                        onClick={handleMicrophone}
                        disabled={busy || paymentBusy}
                        aria-label={
                          recording
                            ? "Stop recording and send audio"
                            : "Start speaking"
                        }
                        aria-pressed={recording}
                      >
                        {recording ? <MicOff size={22} /> : <Mic size={22} />}
                      </button>

                      <div className="mic-copy">
                        <strong>
                          {recording
                            ? "Listening… tap to send"
                            : busy
                              ? "Processing your request"
                              : "Start speaking"}
                        </strong>
                        <span>
                          {recording
                            ? "Speak clearly, then stop recording"
                            : "Your request is sent securely to the demo banking service"}
                        </span>
                      </div>

                      <span
                        className={`recording-label ${
                          recording ? "recording-label-active" : ""
                        }`}
                      >
                        <i />
                        {recording
                          ? "RECORDING"
                          : busy
                            ? "PROCESSING"
                            : "READY"}
                      </span>
                    </div>

                    <div className="composer-bottom">
                      <span className="mock-only-note">
                        <ShieldCheck size={14} />
                        Mock transactions only
                      </span>

                      <div className="composer-actions">
                        <input
                          ref={fileRef}
                          type="file"
                          accept="audio/wav,audio/mpeg,audio/mp4,audio/x-m4a,audio/webm,.m4a,.wav,.mp3,.webm"
                          hidden
                          onChange={handleFileChange}
                        />

                        <button
                          className="secondary-button"
                          disabled={busy || recording || paymentBusy}
                          onClick={() => fileRef.current?.click()}
                        >
                          <Upload size={15} />
                          {selectedAudioFile ? "Replace audio" : "Upload audio"}
                        </button>

                        {selectedAudioFile ? (
                          <button
                            className="primary-button speak-button"
                            disabled={busy || paymentBusy}
                            onClick={() => {
                              const file = selectedAudioFile;
                              setSelectedAudioFile(null);
                              sendAudio(file, file.name);
                            }}
                          >
                            <AudioLines size={15} />
                            Send audio
                          </button>
                        ) : (
                          <button
                            className="primary-button speak-button"
                            disabled={busy || paymentBusy}
                            onClick={handleMicrophone}
                          >
                            {recording ? <MicOff size={15} /> : <Mic size={15} />}
                            {recording ? "Stop recording" : "Speak now"}
                          </button>
                        )}
                      </div>
                    </div>

                    {selectedAudioFile && (
                      <div className="selected-file">
                        <FileAudio size={15} />
                        <span>{selectedAudioFile.name}</span>
                        <small>
                          {(selectedAudioFile.size / (1024 * 1024)).toFixed(2)} MB
                        </small>
                        <button
                          onClick={() => setSelectedAudioFile(null)}
                          aria-label="Clear selected audio file"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                </section>

                <aside className="right-column">
                  <section className="side-card">
                    <div className="side-card-heading">
                      <div>
                        <h3>Quick actions</h3>
                        <p>Jump straight to what you need</p>
                      </div>
                      <Sparkles size={18} />
                    </div>

                    <button
                      className="quick-action"
                      onClick={() => {
                        resetConversation();
                        goTo(assistantRef, "assistant");
                      }}
                    >
                      <span className="quick-icon purple">
                        <AudioLines size={17} />
                      </span>
                      <span>
                        <strong>Start conversation</strong>
                        <small>Talk to your assistant</small>
                      </span>
                      <ChevronRight className="quick-arrow" size={16} />
                    </button>

                    <button
                      className="quick-action"
                      onClick={() => goTo(null, "transactions")}
                    >
                      <span className="quick-icon blue">
                        <ArrowLeftRight size={17} />
                      </span>
                      <span>
                        <strong>Recent transactions</strong>
                        <small>View payment activity</small>
                      </span>
                      <ChevronRight className="quick-arrow" size={16} />
                    </button>

                    <button
                      className="quick-action"
                      onClick={() => goTo(limitsRef, "limits")}
                    >
                      <span className="quick-icon amber">
                        <ShieldCheck size={17} />
                      </span>
                      <span>
                        <strong>Security &amp; limits</strong>
                        <small>Understand demo rules</small>
                      </span>
                      <ChevronRight className="quick-arrow" size={16} />
                    </button>
                  </section>

                  <section className="side-card activity-card">
                    <div className="side-card-heading">
                      <div>
                        <h3>Conversation activity</h3>
                        <p>Current browser session</p>
                      </div>
                      <Clock3 size={18} />
                    </div>

                    <div className="activity-timeline">
                      {messages.slice(-3).reverse().map((message) => (
                        <div className="timeline-item" key={message.id}>
                          <span
                            className={`timeline-dot ${
                              message.kind === "error"
                                ? "error"
                                : message.status === "completed"
                                  ? "success"
                                  : ""
                            }`}
                          />
                          <div>
                            <strong>
                              {message.role === "user"
                                ? "Request received"
                                : message.status === "completed"
                                  ? "Payment completed"
                                  : message.status === "awaiting_confirmation"
                                    ? "Awaiting confirmation"
                                    : message.kind === "error"
                                      ? "Request error"
                                      : "Assistant response"}
                            </strong>
                            <small>
                              {message.time} · {message.text}
                            </small>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="activity-footer">
                      <span
                        className={`status-dot ${
                          backendOnline === false ? "offline" : "online"
                        }`}
                      />
                      {backendOnline === false
                        ? "Backend connection unavailable"
                        : "Session activity is up to date"}
                    </div>
                  </section>

                  <section className="side-card limits-card" ref={limitsRef}>
                    <div className="side-card-heading">
                      <div>
                        <h3>Security &amp; transfer limits</h3>
                        <p>Configured demo rules</p>
                      </div>
                      <ShieldCheck size={18} />
                    </div>

                    <div className="limit-row">
                      <span>Maximum single transfer</span>
                      <strong>₹10,000.00</strong>
                    </div>

                    <div className="limit-row">
                      <span>Daily completed transfers</span>
                      <strong>₹25,000.00</strong>
                    </div>

                    <div className="limit-note">
                      <ShieldCheck size={14} />
                      Demo limits only, not actual bank policy. Every payment
                      requires explicit confirmation.
                    </div>
                  </section>

                  <section className="side-card help-card" ref={helpRef}>
                    <div className="side-card-heading">
                      <div>
                        <h3>Need a hand?</h3>
                        <p>Quick guide</p>
                      </div>
                      <CircleHelp size={18} />
                    </div>

                    <ul>
                      <li>
                        Tap <strong>Speak now</strong> and say the payee and amount.
                      </li>
                      <li>
                        Upload an audio file if your microphone is unavailable.
                      </li>
                      <li>
                        Review pending payments and confirm or cancel them explicitly.
                      </li>
                      <li>
                        If offline, start the FastAPI backend and retry.
                      </li>
                    </ul>

                    <button
                      className="text-action"
                      onClick={() => setShowHelp((value) => !value)}
                    >
                      {showHelp
                        ? "Close assistant guide"
                        : "Open assistant guide"}
                      <ChevronRight size={15} />
                    </button>
                  </section>
                </aside>
              </section>
            </>
          )}

          {currentPage === "transactions" && (
            <section
              className="transactions-page"
              ref={transactionsRef}
            >
              <div className="transactions-page-heading">
                <div>
                  <span className="eyebrow">
                    <ReceiptText size={14} />
                    ACCOUNT ACTIVITY
                  </span>
                  <h1>Transactions</h1>
                  <p>
                    Review your mock payments and their latest status.
                  </p>
                </div>

                <button
                  className="secondary-button"
                  onClick={() =>
                    Promise.all([
                      fetchPaymentHistory({ quiet: true }),
                      fetchCurrentBalance(),
                    ])
                  }
                  disabled={historyRefreshing || historyLoading || balanceLoading}
                >
                  <RefreshCw
                    className={
                      historyRefreshing || balanceLoading ? "spin" : ""
                    }
                    size={15}
                  />
                  {historyRefreshing || balanceLoading
                    ? "Refreshing…"
                    : "Refresh"}
                </button>
              </div>

              <div className="transactions-summary">
                <div>
                  <span>Total completed transfers</span>
                  <strong>{formatINR(completedTransfersTotal)}</strong>
                  <small>Demo activity only · No real money moves</small>
                </div>
                <span className="transactions-summary-icon">
                  <ArrowLeftRight size={22} />
                </span>
              </div>

              <label className="transaction-search">
                <Search size={17} />
                <input
                  type="search"
                  value={transactionSearch}
                  onChange={(event) => setTransactionSearch(event.target.value)}
                  placeholder="Search recipient or transaction ID"
                  aria-label="Search recipient or transaction ID"
                />
              </label>

              <div
                className="transaction-filters"
                role="group"
                aria-label="Filter transactions"
              >
                {[
                  ["all", "All"],
                  ["completed", "Completed"],
                  ["pending", "Pending"],
                  ["failed", "Failed"],
                  ["cancelled", "Cancelled"],
                ].map(([value, label]) => (
                  <button
                    key={value}
                    className={`transaction-filter ${
                      transactionFilter === value ? "active" : ""
                    }`}
                    onClick={() => setTransactionFilter(value)}
                    aria-pressed={transactionFilter === value}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <section className="transactions-card transactions-list-card">
                <div className="transactions-header">
                  <div>
                    <h2>Payment history</h2>
                    <p>
                      {filteredTransactions.length}{" "}
                      {filteredTransactions.length === 1 ? "record" : "records"}{" "}
                      found · Latest 20 records
                    </p>
                  </div>
                </div>

                {historyError && (
                  <div className="transaction-error" role="alert">
                    <AlertCircle size={16} />
                    <span>{historyError}</span>
                    <button
                      onClick={() =>
                        Promise.all([
                          fetchPaymentHistory(),
                          fetchCurrentBalance(),
                        ])
                      }
                    >
                      Try again
                    </button>
                  </div>
                )}

                {!historyError &&
                  historyLoading &&
                  transactions.length === 0 && (
                    <div className="transaction-empty">
                      Loading your transactions…
                    </div>
                  )}

                {!historyError &&
                  !historyLoading &&
                  filteredTransactions.length === 0 && (
                    <EmptyState
                      icon={ArrowLeftRight}
                      title={
                        transactions.length
                          ? "No matching transactions"
                          : "No transactions yet"
                      }
                    >
                      {transactions.length
                        ? "Try a different search or status filter."
                        : "Your mock payments will appear here after you use the voice assistant."}
                    </EmptyState>
                  )}

                {filteredTransactions.length > 0 && (
                  <>
                    <div className="transaction-table-wrap">
                      <table className="transaction-table">
                        <thead>
                          <tr>
                            <th scope="col">Recipient</th>
                            <th scope="col">Date &amp; time (IST)</th>
                            <th scope="col">Status</th>
                            <th scope="col" className="amount-heading">
                              Amount
                            </th>
                            <th scope="col">Action</th>
                          </tr>
                        </thead>

                        <tbody>
                          {filteredTransactions.map((transaction) => {
                            const isPending = [
                              "pending",
                              "pending_confirmation",
                              "awaiting_confirmation",
                            ].includes(
                              normalizedTransactionStatus(transaction)
                            );

                            return (
                              <tr key={transaction.payment_id}>
                                <td>
                                  <div className="table-recipient">
                                    <span className="recipient-icon">
                                      <ArrowUpRight size={17} />
                                    </span>
                                    <span>
                                      <strong>
                                        {transaction.payee_name ||
                                          "Unknown recipient"}
                                      </strong>
                                      <small title={transaction.payment_id}>
                                        {transaction.payment_id}
                                      </small>
                                    </span>
                                  </div>
                                </td>

                                <td className="transaction-date">
                                  {formatTransactionDate(
                                    transaction.created_at
                                  )}
                                </td>

                                <td>
                                  <StatusBadge status={transaction.status} />
                                </td>

                                <td className="transaction-amount-cell">
                                  −{formatINR(transaction.amount)}
                                </td>

                                <td>
                                  {isPending ? (
                                    <div className="transaction-row-actions">
                                      <button
                                        className="transaction-confirm-button"
                                        disabled={paymentBusy}
                                        onClick={() =>
                                          handlePaymentDecision(true, transaction)
                                        }
                                      >
                                        <CheckCircle2 size={14} />
                                        Confirm
                                      </button>

                                      <button
                                        className="transaction-reject-button"
                                        disabled={paymentBusy}
                                        onClick={() =>
                                          handlePaymentDecision(false, transaction)
                                        }
                                      >
                                        <X size={14} />
                                        Reject
                                      </button>
                                    </div>
                                  ) : (
                                    <span className="transaction-no-action">
                                      —
                                    </span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    <div className="mobile-transactions">
                      {filteredTransactions.map((transaction) => {
                        const isPending = [
                          "pending",
                          "pending_confirmation",
                          "awaiting_confirmation",
                        ].includes(
                          normalizedTransactionStatus(transaction)
                        );

                        return (
                          <article
                            className="mobile-transaction-card"
                            key={transaction.payment_id}
                          >
                            <div className="mobile-transaction-top">
                              <span className="recipient-icon">
                                <ArrowUpRight size={17} />
                              </span>

                              <div className="mobile-recipient">
                                <strong>
                                  {transaction.payee_name ||
                                    "Unknown recipient"}
                                </strong>
                                <small>
                                  {formatTransactionDate(
                                    transaction.created_at
                                  )}{" "}
                                  IST
                                </small>
                              </div>

                              <strong className="mobile-amount">
                                −{formatINR(transaction.amount)}
                              </strong>
                            </div>

                            <div className="mobile-transaction-bottom">
                              <StatusBadge status={transaction.status} />
                              <span
                                className="mobile-payment-id"
                                title={transaction.payment_id}
                              >
                                Ref · {transaction.payment_id}
                              </span>
                            </div>

                            {isPending && (
                              <div className="transaction-row-actions mobile-row-actions">
                                <button
                                  className="transaction-confirm-button"
                                  disabled={paymentBusy}
                                  onClick={() =>
                                    handlePaymentDecision(true, transaction)
                                  }
                                >
                                  <CheckCircle2 size={14} />
                                  Confirm
                                </button>

                                <button
                                  className="transaction-reject-button"
                                  disabled={paymentBusy}
                                  onClick={() =>
                                    handlePaymentDecision(false, transaction)
                                  }
                                >
                                  <X size={14} />
                                  Reject
                                </button>
                              </div>
                            )}
                          </article>
                        );
                      })}
                    </div>
                  </>
                )}

                <div className="transactions-footer">
                  <span>
                    Showing {filteredTransactions.length} of{" "}
                    {transactions.length} loaded records
                  </span>
                  <span>Demo only</span>
                </div>
              </section>
            </section>
          )}

          <footer className="page-footer">
            <span>VoxBank · Voice Banking Agent</span>
            <span>
              <ShieldCheck size={14} />
              Prototype only — no real money moves
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
