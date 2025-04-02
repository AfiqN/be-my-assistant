import { escapeHTML, scrollToBottom } from "/static/js/utils.js";
import ApiService from "./apiService.js";

const ChatModule = {
  init(AppState, Elements) {
    this.AppState = AppState;
    this.Elements = Elements;
    this.initCustomerChat();
  },

  initCustomerChat() {
    const { chatForm, clearChatBtn, chatbox, loadingIndicator } =
      this.Elements.customer;

    if (!chatForm) {
      console.warn(
        "Customer chat form not found. Skipping customer event listeners."
      );
      return;
    }

    // Ensure loading indicator is in the chatbox
    if (
      loadingIndicator &&
      chatbox &&
      loadingIndicator.parentNode !== chatbox
    ) {
      chatbox.appendChild(loadingIndicator);
    }

    chatForm.addEventListener("submit", (e) => this.handleChatSubmit(e));
    clearChatBtn.addEventListener("click", () => this.handleClearChat());
  },

  handleChatSubmit(e) {
    e.preventDefault();

    const {
      questionInput,
      sendButton,
      chatbox,
      loadingIndicator,
      welcomeMessage,
    } = this.Elements.customer;

    const question = questionInput.value.trim();
    if (!question) return;

    if (this.AppState.chat.isLoading) return;
    const currentChatHistory = this.AppState.chat.history.slice(0, -1); // Get history *before* the latest user message was added
    this.addUserMessage(question);
    questionInput.value = "";

    // Show loading state
    this.AppState.chat.isLoading = true;
    loadingIndicator.style.display = "block";
    sendButton.disabled = true;
    questionInput.disabled = true;

    // Remove welcome message if present
    if (welcomeMessage && chatbox.contains(welcomeMessage)) {
      chatbox.removeChild(welcomeMessage);
    }

    // Scroll to bottom to show the loading indicator
    scrollToBottom(chatbox);

    ApiService.sendChatMessage(question, currentChatHistory)
      .then((data) => {
        console.log("Customer: Chat success data:", data);
        this.addBotMessage(data.answer);
      })
      .catch((error) => {
        console.error("Customer: Chat Fetch Error:", error);
        this.addBotMessage(
          `Sorry, there was an issue: ${error.message}. Please try asking again.`
        );
      })
      .finally(() => {
        // Hide loading state
        loadingIndicator.style.display = "none";
        this.AppState.chat.isLoading = false;

        console.log("Customer: Chat fetch finished.");
        sendButton.disabled = false;
        questionInput.disabled = false;
        questionInput.focus();
      });
  },

  handleClearChat() {
    const { chatbox, welcomeMessage } = this.Elements.customer;

    console.log("Customer: Clearing chat messages.");

    const messagesToRemove = chatbox.querySelectorAll(".message-container");
    messagesToRemove.forEach((msg) => chatbox.removeChild(msg));

    this.AppState.chat.history = [];

    // Show welcome message again
    if (welcomeMessage && !chatbox.contains(welcomeMessage)) {
      chatbox.appendChild(welcomeMessage);
    }

    scrollToBottom(chatbox);
  },

  addUserMessage(text) {
    const { chatbox, welcomeMessage } = this.Elements.customer;

    if (!chatbox) return;

    const messageDiv = document.createElement("div");
    messageDiv.className = "message-container user-message-container";
    const time = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    messageDiv.innerHTML = `
        <div class="message-content">
          <div class="message-bubble">${escapeHTML(text)}</div>
          <div class="message-time text-end">${time}</div>
        </div>
        <div class="message-avatar">
          <i class="bi bi-person"></i>
        </div>
      `;

    // Remove welcome message if present
    if (welcomeMessage && chatbox.contains(welcomeMessage)) {
      chatbox.removeChild(welcomeMessage);
    }

    chatbox.appendChild(messageDiv);
    scrollToBottom(chatbox);

    this.AppState.chat.history.push({
      role: "user",
      content: text,
      time: time,
    });
  },

  addBotMessage(text) {
    const { chatbox, welcomeMessage } = this.Elements.customer;

    if (!chatbox) return;

    if (text === null || typeof text === "undefined") {
      console.warn("Attempted to add null or undefined bot message.");
      text = "I didn't receive a response.";
    }

    const messageDiv = document.createElement("div");
    messageDiv.className = "message-container bot-message-container";
    const time = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    marked.setOptions({
      breaks: true, // Convert single line breaks to <br>
      gfm: true, // Use GitHub Flavored Markdown
    });
    const rawHtml = marked.parse(text);

    // Sanitize the HTML using DOMPurify to prevent XSS attacks
    // Allow basic formatting tags likely used in Markdown (lists, bold, italics)
    const cleanHtml = DOMPurify.sanitize(rawHtml, {
      USE_PROFILES: { html: true }, // Allow basic HTML tags
      ALLOWED_TAGS: [
        "ul",
        "ol",
        "li",
        "p",
        "b",
        "strong",
        "i",
        "em",
        "br",
        "a",
        "code",
        "pre",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
        "hr",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
      ], // Allow specific tags
      ALLOWED_ATTR: ["href", "title", "target", "class"], // Allow specific attributes
    });

    messageDiv.innerHTML = `
      <div class="message-avatar">
        <i class="bi bi-robot"></i>
      </div>
      <div class="message-content">
        <div class="message-bubble">${cleanHtml}</div>
        <div class="message-time">${time}</div>
        <div class="message-actions">
          <button class="message-action-btn copy-btn" title="Copy raw text" data-raw-text="${escapeHTML(
            text
          )}">
            <i class="bi bi-clipboard"></i> Copy
          </button>
        </div>
      </div>
    `;

    // Remove welcome message if present
    if (welcomeMessage && chatbox.contains(welcomeMessage)) {
      chatbox.removeChild(welcomeMessage);
    }

    chatbox.appendChild(messageDiv);
    scrollToBottom(chatbox);

    this.AppState.chat.history.push({
      role: "assistant",
      content: text,
      time: time,
    });

    // Add copy functionality
    const copyBtn = messageDiv.querySelector(".copy-btn");
    copyBtn.addEventListener("click", () => {
      const rawTextToCopy = copyBtn.getAttribute("data-raw-text"); // Get raw text
      navigator.clipboard
        .writeText(rawTextToCopy)
        .then(() => {
          const originalText = copyBtn.innerHTML;
          copyBtn.innerHTML = '<i class="bi bi-check"></i> Copied';
          copyBtn.disabled = true;

          setTimeout(() => {
            copyBtn.innerHTML = originalText;
            copyBtn.disabled = false;
          }, 2000);
        })
        .catch((err) => {
          console.error("Failed to copy text: ", err);
        });
    });
  },
};

export default ChatModule;
