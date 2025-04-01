document.addEventListener("DOMContentLoaded", function () {
  // Initialize AOS animations
  AOS.init({
    duration: 800,
    once: true,
  });

  // ============================
  // === APP STATE MANAGEMENT ===
  // ============================
  const AppState = {
    currentView: "customer-view",
    admin: {
      currentFile: null,
      processedFiles: [],
      isUploading: false,
    },
    chat: {
      history: [],
      isLoading: false,
    },
  };

  // ============================
  // === DOM ELEMENT REFERENCES ===
  // ============================
  const Elements = {
    // View containers
    views: {
      admin: document.getElementById("admin-view"),
      customer: document.getElementById("customer-view"),
    },

    // Navigation
    nav: {
      adminBtn: document.getElementById("switchToAdminBtn"),
      customerBtn: document.getElementById("switchToCustomerBtn"),
      aboutBtn: document.getElementById("aboutBtn"),
    },

    // Header
    header: {
      title: document.getElementById("viewTitle"),
      subtitle: document.getElementById("viewSubtitle"),
    },

    // Admin view elements
    admin: {
      uploadForm: document.getElementById("uploadForm"),
      fileInput: document.getElementById("fileInput"),
      browseBtn: document.getElementById("browseBtn"),
      selectedFileDiv: document.getElementById("selectedFile"),
      uploadBtn: document.getElementById("uploadBtn"),
      uploadStatus: document.getElementById("uploadStatus"),
      documentList: document.getElementById("documentList"),
    },

    // Customer view elements
    customer: {
      chatForm: document.getElementById("chatForm"),
      questionInput: document.getElementById("questionInput"),
      sendButton: document.getElementById("sendButton"),
      clearChatBtn: document.getElementById("clearChatBtn"),
      chatbox: document.getElementById("chatbox"),
      loadingIndicator: document.getElementById("loadingIndicator"),
      welcomeMessage: document.querySelector("#customer-view .welcome-message"),
    },

    // Modal
    modal: {
      about: new bootstrap.Modal(document.getElementById("aboutModal")),
    },
  };

  // ============================
  // === VIEW MANAGEMENT ===
  // ============================
  function initViewSwitcher() {
    // Set initial view
    switchView(AppState.currentView);

    // Add event listeners for view switching
    Elements.nav.adminBtn.addEventListener("click", () =>
      switchView("admin-view")
    );
    Elements.nav.customerBtn.addEventListener("click", () =>
      switchView("customer-view")
    );
    Elements.nav.aboutBtn.addEventListener("click", (e) => {
      e.preventDefault();
      Elements.modal.about.show();
    });
  }

  function switchView(viewId) {
    console.log(`Switching to view: ${viewId}`);

    // Update active button styling
    document.querySelectorAll(".nav-link").forEach((link) => {
      link.classList.remove("active");
    });

    if (viewId === "admin-view") {
      Elements.nav.adminBtn.classList.add("active");
      if (Elements.header.title)
        Elements.header.title.textContent = "Admin Dashboard";
      if (Elements.header.subtitle)
        Elements.header.subtitle.textContent = "Manage AI Assistant Context";
    } else {
      Elements.nav.customerBtn.classList.add("active");
      if (Elements.header.title)
        Elements.header.title.textContent = "Customer View";
      if (Elements.header.subtitle)
        Elements.header.subtitle.textContent = "AI Powered Customer Service";
    }

    // Hide all views
    document.querySelectorAll(".view-section").forEach((section) => {
      section.style.display = "none";
      section.classList.remove("active");
    });

    // Show selected view
    const viewToShow = document.getElementById(viewId);
    if (viewToShow) {
      viewToShow.style.display = "flex";
      viewToShow.classList.add("active");
      AppState.currentView = viewId;
    } else {
      console.error(`View with id ${viewId} not found!`);
    }
  }

  // ============================
  // === ADMIN: FILE UPLOAD ===
  // ============================
  function initAdminFileUpload() {
    const { uploadForm, fileInput, browseBtn, uploadBtn } = Elements.admin;

    if (!uploadForm) {
      console.warn(
        "Admin upload form not found. Skipping admin event listeners."
      );
      return;
    }

    // File input handling
    fileInput.addEventListener("change", handleFileSelection);
    browseBtn.addEventListener("click", () => fileInput.click());

    // File drop area
    const fileDropArea = Elements.views.admin.querySelector(".file-drop-area");
    if (fileDropArea) {
      ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
        fileDropArea.addEventListener(eventName, preventDefaults);
      });

      ["dragenter", "dragover"].forEach((eventName) => {
        fileDropArea.addEventListener(eventName, () => {
          fileDropArea.classList.add("dragover");
        });
      });

      ["dragleave", "drop"].forEach((eventName) => {
        fileDropArea.addEventListener(eventName, () => {
          fileDropArea.classList.remove("dragover");
        });
      });

      fileDropArea.addEventListener("drop", handleFileDrop);
    }

    // Form submission
    uploadForm.addEventListener("submit", handleUploadSubmit);

    // Initial UI state
    updateDocumentList();
    uploadBtn.disabled = true;
  }

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  function handleFileDrop(e) {
    const { fileInput } = Elements.admin;
    const files = e.dataTransfer.files;

    if (files.length) {
      fileInput.files = files;
      handleFileSelection();
    }
  }

  function handleFileSelection() {
    const { fileInput, selectedFileDiv, uploadBtn } = Elements.admin;

    console.log("Admin: handleFileSelection triggered.");

    if (fileInput.files.length > 0) {
      const file = fileInput.files[0];
      console.log("Admin: File selected:", file.name, file.type);

      if (file.type !== "application/pdf") {
        showAdminStatus("Please upload a PDF document.", "error");
        fileInput.value = "";
        selectedFileDiv.innerHTML = "";
        selectedFileDiv.style.display = "none";
        AppState.admin.currentFile = null;
        uploadBtn.disabled = true;
        console.log("Admin: Invalid file type.");
        return;
      }

      AppState.admin.currentFile = file;
      selectedFileDiv.innerHTML = `
          <i class="bi bi-file-earmark-pdf-fill"></i> 
          ${escapeHTML(file.name)} (${formatFileSize(file.size)})
        `;
      selectedFileDiv.style.display = "flex";
      uploadBtn.disabled = false;
      showAdminStatus("", "clear");
      console.log(
        "Admin: Valid file selected. currentFile set to:",
        AppState.admin.currentFile
      );
    } else {
      console.log("Admin: No file selected in input.");
      selectedFileDiv.innerHTML = "";
      selectedFileDiv.style.display = "none";
      AppState.admin.currentFile = null;
      uploadBtn.disabled = true;
    }
  }

  function handleUploadSubmit(e) {
    e.preventDefault();

    const { uploadBtn, fileInput } = Elements.admin;

    console.log("Admin: Upload form submitted.");

    if (!AppState.admin.currentFile) {
      console.log("Admin: currentFile is null or empty.");
      showAdminStatus("Please select a PDF file first.", "error");
      return;
    }

    if (AppState.admin.isUploading) {
      console.log("Admin: Upload already in progress.");
      return;
    }

    AppState.admin.isUploading = true;
    showAdminStatus(
      '<div class="spinner-border spinner-border-sm me-2" role="status"></div> Processing document...',
      "loading"
    );
    uploadBtn.disabled = true;
    fileInput.disabled = true;

    const formData = new FormData();
    formData.append("file", AppState.admin.currentFile);

    fetch("/api/v1/upload", {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        console.log("Admin: Fetch response received:", response.status);

        if (!response.ok) {
          return response
            .json()
            .then((errData) => {
              console.error("Admin: Backend error response:", errData);
              throw new Error(
                errData.detail || `HTTP error! status: ${response.status}`
              );
            })
            .catch((jsonError) => {
              console.error(
                "Admin: Failed to parse backend error JSON or generic HTTP error:",
                jsonError
              );
              throw new Error(`HTTP error! status: ${response.status}`);
            });
        }

        return response.json();
      })
      .then((data) => {
        console.log("Admin: Upload successful. Backend data:", data);
        showAdminStatus(
          `
          <i class="bi bi-check-circle"></i> 
          ${data.message || "Context successfully processed!"} 
          (${data.chunks_added} sections added)
        `,
          "success"
        );

        // Add to processed files list
        AppState.admin.processedFiles.push(data.filename);
        updateDocumentList();

        // Reset file input
        fileInput.value = "";
        Elements.admin.selectedFileDiv.innerHTML = "";
        Elements.admin.selectedFileDiv.style.display = "none";
        AppState.admin.currentFile = null;
      })
      .catch((error) => {
        console.error("Admin: Upload Fetch Error:", error);
        showAdminStatus(
          `<i class="bi bi-exclamation-triangle"></i> Error: ${error.message}`,
          "error"
        );
      })
      .finally(() => {
        console.log("Admin: Fetch finished. Re-enabling buttons.");
        AppState.admin.isUploading = false;
        uploadBtn.disabled = false;
        fileInput.disabled = false;
        handleFileSelection();
      });
  }

  function showAdminStatus(message, type) {
    const { uploadStatus } = Elements.admin;

    if (!uploadStatus) return;

    if (type === "clear") {
      uploadStatus.innerHTML = "";
      return;
    }

    uploadStatus.innerHTML = "";

    const statusDiv = document.createElement("div");
    const autoClear = type === "error" || type === "success";
    statusDiv.className = `status-message ${type} ${
      autoClear ? "fade-in" : ""
    }`;
    statusDiv.innerHTML = message;
    uploadStatus.appendChild(statusDiv);

    if (autoClear) {
      setTimeout(() => {
        statusDiv.classList.add("fade-out");
        setTimeout(() => {
          if (uploadStatus.contains(statusDiv)) {
            uploadStatus.removeChild(statusDiv);
          }
        }, 500);
      }, 5000);
    }
  }

  function updateDocumentList() {
    const { documentList } = Elements.admin;

    if (!documentList) return;

    documentList.innerHTML = "";

    if (AppState.admin.processedFiles.length === 0) {
      documentList.innerHTML =
        '<li class="list-group-item text-muted"><em>No processed documents yet.</em></li>';
    } else {
      AppState.admin.processedFiles.forEach((filename) => {
        const li = document.createElement("li");
        li.className = "list-group-item";
        li.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <i class="bi bi-file-earmark-text me-2"></i>
                ${escapeHTML(filename)}
              </div>
              <button class="btn btn-sm btn-outline-danger delete-doc-btn" data-filename="${escapeHTML(
                filename
              )}">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        documentList.appendChild(li);
      });

      // Add event listeners to delete buttons
      documentList.querySelectorAll(".delete-doc-btn").forEach((btn) => {
        btn.addEventListener("click", function () {
          const filenameToDelete = this.getAttribute("data-filename");
          const buttonElement = this; // Keep reference to the button

          // Disable button immediately
          buttonElement.disabled = true;
          buttonElement.innerHTML =
            '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

          console.log(`Attempting to delete context for: ${filenameToDelete}`);

          // Call the backend API endpoint
          fetch(
            `/api/v1/delete_context/${encodeURIComponent(filenameToDelete)}`,
            {
              // URL-encode filename
              method: "DELETE",
            }
          )
            .then((response) => {
              if (!response.ok) {
                // If status is not 2xx, especially not 204
                return response
                  .json()
                  .then((errData) => {
                    console.error("Backend delete error response:", errData);
                    throw new Error(
                      errData.detail || `HTTP error! status: ${response.status}`
                    );
                  })
                  .catch((jsonError) => {
                    console.error(
                      "Failed to parse backend error JSON or generic HTTP error:",
                      jsonError
                    );
                    throw new Error(`HTTP error! status: ${response.status}`);
                  });
              }
              // If response is OK (e.g., 204 No Content), proceed
              console.log(
                `Successfully deleted context for: ${filenameToDelete} from backend.`
              );
              return null; // Or handle 204 explicitly
            })
            .then(() => {
              // --- Success: Update frontend state and UI ---
              AppState.admin.processedFiles =
                AppState.admin.processedFiles.filter(
                  (f) => f !== filenameToDelete
                );
              updateDocumentList(); // Re-render the list which will remove the item
              showAdminStatus(
                `<i class="bi bi-check-circle"></i> Context "${escapeHTML(
                  filenameToDelete
                )}" removed successfully.`,
                "success"
              );
            })
            .catch((error) => {
              // --- Failure: Show error and re-enable button ---
              console.error("Error deleting context:", error);
              showAdminStatus(
                `<i class="bi bi-exclamation-triangle"></i> Error removing context "${escapeHTML(
                  filenameToDelete
                )}": ${error.message}`,
                "error"
              );
              // Re-enable the button only on error, as success removes it via updateDocumentList()
              if (document.contains(buttonElement)) {
                // Check if button still exists before re-enabling
                buttonElement.disabled = false;
                buttonElement.innerHTML = '<i class="bi bi-trash"></i>';
              }
            });
        });
      });
    }
  }

  // ============================
  // === CUSTOMER: CHAT ===
  // ============================
  function initCustomerChat() {
    const { chatForm, clearChatBtn, chatbox, loadingIndicator } =
      Elements.customer;

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

    chatForm.addEventListener("submit", handleChatSubmit);
    clearChatBtn.addEventListener("click", handleClearChat);
  }

  function handleChatSubmit(e) {
    e.preventDefault();

    const {
      questionInput,
      sendButton,
      chatbox,
      loadingIndicator,
      welcomeMessage,
    } = Elements.customer;

    const question = questionInput.value.trim();
    if (!question) return;

    if (AppState.chat.isLoading) return;

    addUserMessage(question);
    questionInput.value = "";

    // Show loading state
    AppState.chat.isLoading = true;
    loadingIndicator.style.display = "block";
    sendButton.disabled = true;
    questionInput.disabled = true;

    // Remove welcome message if present
    if (welcomeMessage && chatbox.contains(welcomeMessage)) {
      chatbox.removeChild(welcomeMessage);
    }

    // Scroll to bottom to show the loading indicator
    scrollToBottom();

    fetch("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question }),
    })
      .then((response) => {
        console.log("Customer: Chat fetch response received:", response.status);

        if (!response.ok) {
          return response
            .json()
            .then((errData) => {
              console.error("Customer: Backend chat error:", errData);
              throw new Error(
                errData.detail || `HTTP error! status: ${response.status}`
              );
            })
            .catch((jsonError) => {
              console.error(
                "Customer: Failed to parse backend error JSON or generic HTTP error:",
                jsonError
              );
              throw new Error(`HTTP error! status: ${response.status}`);
            });
        }

        return response.json();
      })
      .then((data) => {
        console.log("Customer: Chat success data:", data);
        addBotMessage(data.answer);
      })
      .catch((error) => {
        console.error("Customer: Chat Fetch Error:", error);
        addBotMessage(
          `Sorry, there was an issue: ${error.message}. Please try asking again.`
        );
      })
      .finally(() => {
        // Hide loading state
        loadingIndicator.style.display = "none";
        AppState.chat.isLoading = false;

        console.log("Customer: Chat fetch finished.");
        sendButton.disabled = false;
        questionInput.disabled = false;
        questionInput.focus();
      });
  }

  function handleClearChat() {
    const { chatbox, welcomeMessage } = Elements.customer;

    console.log("Customer: Clearing chat messages.");

    const messagesToRemove = chatbox.querySelectorAll(".message-container");
    messagesToRemove.forEach((msg) => chatbox.removeChild(msg));

    AppState.chat.history = [];

    // Show welcome message again
    if (welcomeMessage && !chatbox.contains(welcomeMessage)) {
      chatbox.appendChild(welcomeMessage);
    }

    scrollToBottom();
  }

  function addUserMessage(text) {
    const { chatbox, welcomeMessage } = Elements.customer;

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
    scrollToBottom();

    AppState.chat.history.push({ role: "user", content: text, time: time });
  }

  function addBotMessage(text) {
    const { chatbox, welcomeMessage } = Elements.customer;

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

    messageDiv.innerHTML = `
        <div class="message-avatar">
          <i class="bi bi-robot"></i>
        </div>
        <div class="message-content">
          <div class="message-bubble">${escapeHTML(text)}</div>
          <div class="message-time">${time}</div>
          <div class="message-actions">
            <button class="message-action-btn copy-btn" title="Copy to clipboard">
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
    scrollToBottom();

    AppState.chat.history.push({
      role: "assistant",
      content: text,
      time: time,
    });

    // Add copy functionality
    const copyBtn = messageDiv.querySelector(".copy-btn");
    copyBtn.addEventListener("click", () => {
      navigator.clipboard
        .writeText(text)
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
  }

  // ============================
  // === UTILITY FUNCTIONS ===
  // ============================
  function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " bytes";
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    else return (bytes / 1048576).toFixed(1) + " MB";
  }

  function escapeHTML(str) {
    if (typeof str !== "string") return "";
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function scrollToBottom() {
    const { chatbox } = Elements.customer;
    if (chatbox) {
      chatbox.scrollTop = chatbox.scrollHeight;
    }
  }

  // ============================
  // === INITIALIZE APP ===
  // ============================
  function initApp() {
    // Initialize view switcher
    initViewSwitcher();

    // Initialize admin functionality
    initAdminFileUpload();

    // Initialize customer chat
    initCustomerChat();
  }

  // Start the application
  initApp();
});
