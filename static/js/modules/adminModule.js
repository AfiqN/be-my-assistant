// File: be-my-assistant/static/js/modules/adminModule.js

import { escapeHTML, formatFileSize } from "/static/js/utils.js";
import ApiService from "./apiService.js";

const AdminModule = {
  init(AppState, Elements) {
    this.AppState = AppState;
    this.Elements = Elements;
    this.initAdminFileUpload();
    this.initAdminPreview();
    this.initAdminPersona();
  },

  // --- Admin File Upload Logic ---
  initAdminFileUpload() {
    const { uploadForm, fileInput, browseBtn, uploadBtn } = this.Elements.admin;
    if (!uploadForm) {
      console.warn(
        "Admin upload form not found. Skipping admin event listeners."
      );
      return;
    }
    fileInput.addEventListener("change", () => this.handleFileSelection());
    browseBtn.addEventListener("click", () => fileInput.click());
    const fileDropArea =
      this.Elements.views.admin.querySelector(".file-drop-area");
    if (fileDropArea) {
      ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
        fileDropArea.addEventListener(eventName, this.preventDefaults);
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
      fileDropArea.addEventListener("drop", (e) => this.handleFileDrop(e));
    }
    uploadForm.addEventListener("submit", (e) => this.handleUploadSubmit(e));
    this.updateDocumentList(); // Initial load
    uploadBtn.disabled = true; // Start disabled
  },

  preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  },

  handleFileDrop(e) {
    const { fileInput } = this.Elements.admin;
    const files = e.dataTransfer.files;
    if (files.length) {
      fileInput.files = files;
      this.handleFileSelection();
    }
  },

  handleFileSelection() {
    const { fileInput, selectedFileDiv, uploadBtn } = this.Elements.admin;
    if (fileInput.files.length > 0) {
      const file = fileInput.files[0];
      // Relaxed validation relying more on backend (but still good to have basic check)
      const allowedExtensions = ["pdf", "txt", "docx", "md"];
      const fileExtension = file.name.split(".").pop().toLowerCase();

      if (!allowedExtensions.includes(fileExtension)) {
        console.warn(
          `Frontend validation: File extension '${fileExtension}' might not be supported by backend.`
        );
        // Optionally show a less strict warning or allow upload and let backend decide
      }

      // Basic type check (can be spoofed but better than nothing)
      const allowedMIMETypes = [
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/markdown",
        "text/x-markdown", // Another common MD type
      ];
      if (
        !allowedMIMETypes.includes(file.type) &&
        !allowedExtensions.includes(fileExtension)
      ) {
        this.showAdminStatus(
          `Unsupported file type or extension. Please use PDF, TXT, DOCX, or MD.`,
          "error",
          this.Elements.admin.uploadStatus
        );
        fileInput.value = ""; // Clear selection
        selectedFileDiv.innerHTML = "";
        selectedFileDiv.style.display = "none";
        this.AppState.admin.currentFile = null;
        uploadBtn.disabled = true;
        return;
      }

      this.AppState.admin.currentFile = file;
      selectedFileDiv.innerHTML = `<i class="bi bi-file-earmark-text-fill me-1"></i> ${escapeHTML(
        file.name
      )} (${formatFileSize(file.size)})`;
      selectedFileDiv.style.display = "flex";
      uploadBtn.disabled = false;
      this.showAdminStatus("", "clear", this.Elements.admin.uploadStatus);
    } else {
      selectedFileDiv.innerHTML = "";
      selectedFileDiv.style.display = "none";
      this.AppState.admin.currentFile = null;
      uploadBtn.disabled = true;
    }
  },

  handleUploadSubmit(e) {
    e.preventDefault();
    const { uploadBtn, fileInput, selectedFileDiv } = this.Elements.admin; // Added selectedFileDiv
    if (!this.AppState.admin.currentFile) {
      this.showAdminStatus(
        "Please select a file first.",
        "error",
        this.Elements.admin.uploadStatus
      );
      return;
    }
    if (this.AppState.admin.isUploading) return;
    this.AppState.admin.isUploading = true;
    this.showAdminStatus(
      '<div class="spinner-border spinner-border-sm me-2" role="status"></div> Processing...',
      "loading",
      this.Elements.admin.uploadStatus
    );
    uploadBtn.disabled = true;
    fileInput.disabled = true;
    ApiService.uploadFile(this.AppState.admin.currentFile)
      .then((data) => {
        this.showAdminStatus(
          `<i class="bi bi-check-circle"></i> ${
            data.message || "Processed!"
          } (${data.chunks_added} sections added)`,
          "success",
          this.Elements.admin.uploadStatus
        );
        // Update document list state only if file wasn't already there
        if (!this.AppState.admin.processedFiles.includes(data.filename)) {
          this.AppState.admin.processedFiles.push(data.filename);
        }
        this.updateDocumentList(); // Refresh the displayed list

        // Clear the file input and selection display
        fileInput.value = "";
        selectedFileDiv.innerHTML = "";
        selectedFileDiv.style.display = "none";
        this.AppState.admin.currentFile = null;
      })
      .catch((error) => {
        this.showAdminStatus(
          `<i class="bi bi-exclamation-triangle"></i> Error: ${error.message}`,
          "error",
          this.Elements.admin.uploadStatus
        );
      })
      .finally(() => {
        this.AppState.admin.isUploading = false;
        // Keep upload button disabled until a new file is selected
        uploadBtn.disabled = true;
        fileInput.disabled = false;
      });
  },

  showAdminStatus(message, type, targetElement) {
    if (!targetElement) return;
    // Clear existing status messages immediately unless it's 'clear' command
    if (type !== "clear") {
      targetElement.innerHTML = "";
    } else {
      targetElement.innerHTML = ""; // Handle clear command
      return;
    }

    const statusDiv = document.createElement("div");
    const autoClear = type === "error" || type === "success"; // Auto clear for success/error
    statusDiv.className = `status-message ${type} ${
      autoClear ? "fade-in" : ""
    }`;
    statusDiv.innerHTML = message;
    targetElement.appendChild(statusDiv);

    // Set timeout for auto-clearing success/error messages
    if (autoClear) {
      setTimeout(() => {
        statusDiv.classList.add("fade-out");
        // Remove the element after the fade-out animation completes
        setTimeout(() => {
          if (targetElement.contains(statusDiv)) {
            targetElement.removeChild(statusDiv);
          }
        }, 500); // Match fade-out duration
      }, 5000); // Duration before starting fade-out
    }
  },

  // Fetches the current list of processed documents from backend (optional, depends on API)
  // For now, it manages the list in frontend state based on uploads/deletions.
  fetchProcessedFiles() {
    // Example if you add an API endpoint /api/v1/documents
    /*
      ApiService.getDocuments()
          .then(data => {
              this.AppState.admin.processedFiles = data.documents || [];
              this.updateDocumentList();
          })
          .catch(error => {
              console.error("Error fetching document list:", error);
              this.showAdminStatus("Could not fetch document list.", "error", this.Elements.admin.uploadStatus);
              // Keep existing list or clear it? For now, keep it.
          });
      */
    // Since we don't have that endpoint, just update based on current state
    console.log(
      "Updating document list based on AppState:",
      this.AppState.admin.processedFiles
    );
    this.updateDocumentList();
  },

  updateDocumentList() {
    const { documentList } = this.Elements.admin;
    if (!documentList) return;
    documentList.innerHTML = ""; // Clear current list

    if (this.AppState.admin.processedFiles.length === 0) {
      documentList.innerHTML =
        '<li class="list-group-item text-muted"><em>No processed documents yet. Upload a file to begin.</em></li>';
    } else {
      // Sort files alphabetically for consistent display
      const sortedFiles = [...this.AppState.admin.processedFiles].sort((a, b) =>
        a.localeCompare(b)
      );

      sortedFiles.forEach((filename) => {
        const li = document.createElement("li");
        li.className = "list-group-item";
        li.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <i class="bi bi-file-earmark-text me-2"></i>${escapeHTML(
                      filename
                    )}
                </div>
                <button class="btn btn-sm btn-outline-danger delete-doc-btn" data-filename="${escapeHTML(
                  filename
                )}" title="Delete context for ${escapeHTML(filename)}">
                    <i class="bi bi-trash"></i>
                </button>
            </div>`;
        documentList.appendChild(li);
      });

      // Add event listeners to the delete buttons AFTER they are created
      const self = this; // Keep reference to AdminModule object
      documentList.querySelectorAll(".delete-doc-btn").forEach((btn) => {
        btn.addEventListener("click", function () {
          const filenameToDelete = this.getAttribute("data-filename");
          // Confirmation dialog
          if (
            !confirm(
              `Are you sure you want to delete the context for "${filenameToDelete}"? This cannot be undone.`
            )
          ) {
            return; // Stop if user cancels
          }

          const buttonElement = this; // Reference to the button clicked
          buttonElement.disabled = true; // Disable button during operation
          buttonElement.innerHTML =
            '<span class="spinner-border spinner-border-sm" role="status"></span>'; // Show spinner

          ApiService.deleteContext(filenameToDelete)
            .then(() => {
              // Remove from frontend state
              self.AppState.admin.processedFiles =
                self.AppState.admin.processedFiles.filter(
                  (f) => f !== filenameToDelete
                );
              // Update the list display
              self.updateDocumentList();
              self.showAdminStatus(
                `<i class="bi bi-check-circle"></i> Context for "${escapeHTML(
                  filenameToDelete
                )}" removed successfully.`,
                "success",
                self.Elements.admin.uploadStatus // Show status near upload area
              );
            })
            .catch((error) => {
              self.showAdminStatus(
                `<i class="bi bi-exclamation-triangle"></i> Error removing context for "${escapeHTML(
                  filenameToDelete
                )}": ${error.message}`,
                "error",
                self.Elements.admin.uploadStatus
              );
              // Re-enable the button if the element still exists
              if (document.body.contains(buttonElement)) {
                buttonElement.disabled = false;
                buttonElement.innerHTML = '<i class="bi bi-trash"></i>';
              }
            });
        });
      });
    }
  },
  // --- End Admin File Upload Logic ---

  // --- Admin Preview Logic ---
  initAdminPreview() {
    const { previewSubmitBtn, previewForm } = this.Elements.admin;

    if (!previewSubmitBtn || !previewForm) {
      console.warn(
        "Admin preview elements (button or form) not found. Skipping preview listeners."
      );
      return;
    }

    // Listener for button click
    previewSubmitBtn.addEventListener("click", (e) =>
      this.handlePreviewSubmit(e)
    );

    // Listener for form submit (e.g., pressing Enter in the input field)
    previewForm.addEventListener("submit", (e) => {
      e.preventDefault(); // Prevent default form submission
      previewSubmitBtn.click(); // Trigger the button click handler
    });
  },

  handlePreviewSubmit(e) {
    // e.preventDefault(); // Already handled by form submit listener

    const {
      previewQuestionInput,
      previewSubmitBtn,
      previewSpinner,
      previewResults,
      retrievedChunksList,
      draftAnswer,
      previewStatus, // Make sure this element exists in elements.js and index.html
    } = this.Elements.admin;

    const question = previewQuestionInput.value.trim();
    if (!question) {
      this.showAdminStatus(
        "Please enter a question to test.",
        "error",
        previewStatus // Use the dedicated preview status element
      );
      return;
    }

    // --- UI: Show Loading State ---
    this.showAdminStatus("", "clear", previewStatus); // Clear previous preview status
    previewSubmitBtn.disabled = true;
    previewSpinner.style.display = "inline-block";
    const buttonIcon = previewSubmitBtn.querySelector("i.bi-play-circle");
    if (buttonIcon) buttonIcon.style.display = "none";
    previewResults.style.display = "none"; // Hide results section initially
    retrievedChunksList.innerHTML =
      '<li class="list-group-item text-muted"><em><div class="spinner-border spinner-border-sm me-1" role="status"></div> Retrieving context...</em></li>';
    draftAnswer.innerHTML =
      '<em class="text-muted"><div class="spinner-border spinner-border-sm me-1" role="status"></div> Generating draft...</em>';

    // --- API Call ---
    ApiService.getAdminPreview(question)
      .then((data) => {
        previewResults.style.display = "block"; // Show results section
        console.log("Admin Preview Response:", data);

        // Display Retrieved Chunks with Show/Hide logic
        retrievedChunksList.innerHTML = ""; // Clear loading state
        if (data.retrieved_chunks && data.retrieved_chunks.length > 0) {
          data.retrieved_chunks.forEach((chunk) => {
            const li = document.createElement("li");
            // Use list-group-item for Bootstrap styling
            li.className = "list-group-item retrieved-chunks-list"; // Add custom class if needed

            const chunkId = `chunk-${Math.random().toString(36).substr(2, 9)}`;
            const contentPreview = chunk.content_preview || "";
            const fullContent = chunk.full_content || chunk.content_preview; // Fallback

            // Check if full content is longer than preview
            const hasMoreContent = fullContent.length > contentPreview.length;

            // If full content starts with preview, only show the additional content when expanded
            let additionalContent = fullContent;
            if (hasMoreContent && fullContent.startsWith(contentPreview)) {
              additionalContent = fullContent.substring(contentPreview.length);
            }

            li.innerHTML = `
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <div class="fw-bold mb-1">Source: ${escapeHTML(
                    chunk.source || "Unknown"
                  )}</div>
                  <small class="text-muted d-block mb-2">Distance: ${
                    chunk.distance !== null ? chunk.distance.toFixed(4) : "N/A"
                  }</small>
                  <p class="mb-1 context-preview small">${escapeHTML(
                    contentPreview
                  )}</p>
                </div>
                ${
                  hasMoreContent
                    ? `
                <button class="btn btn-sm btn-link p-0 flex-shrink-0 ms-2"
                        type="button"
                        data-bs-toggle="collapse"
                        data-bs-target="#${chunkId}"
                        aria-expanded="false"
                        aria-controls="${chunkId}"
                        title="Toggle full context">
                  <span class="collapsed-text"><i class="bi bi-arrows-expand"></i> Show More</span>
                  <span class="expanded-text" style="display:none;"><i class="bi bi-arrows-collapse"></i> Hide</span>
                </button>
                `
                    : ""
                }
              </div>
              ${
                hasMoreContent
                  ? `
              <div class="collapse" id="${chunkId}">
                <div class="card card-body p-2 mt-2 mb-2 bg-light small context-full-text">
                  ${escapeHTML(additionalContent)}
                </div>
              </div>
              `
                  : ""
              }
            `;
            retrievedChunksList.appendChild(li);
          });

          // Add event listeners for the Bootstrap collapse events AFTER rendering all items
          retrievedChunksList
            .querySelectorAll('[data-bs-toggle="collapse"]')
            .forEach((button) => {
              const targetCollapse = document.querySelector(
                button.getAttribute("data-bs-target")
              );
              if (!targetCollapse) return; // Skip if target not found

              // Listener when the collapse element starts to show
              targetCollapse.addEventListener("show.bs.collapse", function () {
                const collapsedText = button.querySelector(".collapsed-text");
                const expandedText = button.querySelector(".expanded-text");
                if (collapsedText) collapsedText.style.display = "none";
                if (expandedText) expandedText.style.display = "inline";
                button.setAttribute("aria-expanded", "true");
              });

              // Listener when the collapse element starts to hide
              targetCollapse.addEventListener("hide.bs.collapse", function () {
                const collapsedText = button.querySelector(".collapsed-text");
                const expandedText = button.querySelector(".expanded-text");
                if (collapsedText) collapsedText.style.display = "inline";
                if (expandedText) expandedText.style.display = "none";
                button.setAttribute("aria-expanded", "false");
              });
            });
        } else {
          retrievedChunksList.innerHTML =
            '<li class="list-group-item text-muted"><em>No relevant context chunks found for this question.</em></li>';
        }

        // Display Draft Answer using marked and DOMPurify
        if (data.draft_answer && data.draft_answer.startsWith("Error:")) {
          draftAnswer.innerHTML = `<div class="alert alert-warning p-2 small" role="alert">${escapeHTML(
            data.draft_answer // Show backend error message safely
          )}</div>`;
        } else if (data.draft_answer) {
          // Ensure marked and DOMPurify are loaded (usually in index.html)
          if (
            typeof marked !== "undefined" &&
            typeof DOMPurify !== "undefined"
          ) {
            marked.setOptions({ breaks: true, gfm: true }); // Convert line breaks, use GitHub Flavored Markdown
            const rawHtml = marked.parse(data.draft_answer);
            const cleanHtml = DOMPurify.sanitize(rawHtml, {
              USE_PROFILES: { html: true },
            }); // Sanitize for safety
            draftAnswer.innerHTML = cleanHtml;
          } else {
            console.warn(
              "marked.js or DOMPurify not loaded. Displaying raw text."
            );
            draftAnswer.innerHTML = `<pre class="small">${escapeHTML(
              data.draft_answer
            )}</pre>`; // Fallback to preformatted text
          }
        } else {
          draftAnswer.innerHTML =
            '<em class="text-muted small">No draft answer generated (or the answer was empty).</em>';
        }
      })
      .catch((error) => {
        console.error("Admin Preview Fetch/Processing Error:", error);
        this.showAdminStatus(
          `<i class="bi bi-exclamation-triangle"></i> Preview Error: ${error.message}`,
          "error",
          previewStatus // Show error in the preview status area
        );
        // Reset preview display on error
        previewResults.style.display = "none";
        retrievedChunksList.innerHTML =
          '<li class="list-group-item text-muted"><em>An error occurred retrieving context.</em></li>';
        draftAnswer.innerHTML =
          '<em class="text-muted">An error occurred generating the draft answer.</em>';
      })
      .finally(() => {
        // --- UI: Hide Loading State ---
        previewSubmitBtn.disabled = false;
        previewSpinner.style.display = "none";
        if (buttonIcon) buttonIcon.style.display = "inline-block"; // Restore icon
      });
  },

  initAdminPersona() {
    const { personaForm, savePersonaBtn } = this.Elements.admin;
    if (!personaForm) {
      console.warn("Admin persona form not found. Skipping persona listeners.");
      return;
    }

    // Load existing settings when the module initializes (or when view becomes active)
    this.loadPersonaSettings();

    // Add listener for the save button (using form submit event)
    personaForm.addEventListener("submit", (e) => this.handleSavePersona(e));
  },

  /**
   * Fetches current persona settings and populates the form.
   */
  loadPersonaSettings() {
    const {
      aiNameInput,
      aiRoleSelect,
      aiToneInput,
      aiCompanyInput,
      personaStatus,
    } = this.Elements.admin;
    if (!aiNameInput || !aiRoleSelect || !aiToneInput || !aiCompanyInput)
      return; // Check if elements exist

    this.showAdminStatus(
      "Loading persona settings...",
      "loading",
      personaStatus
    );

    ApiService.getCurrentPersona()
      .then((settings) => {
        aiNameInput.value = "";
        aiRoleSelect.value = "";
        aiToneInput.value = "";
        aiCompanyInput.value = "";
        this.showAdminStatus("", "clear", personaStatus); // Clear loading message
        console.info("Persona settings loaded into form.");
      })
      .catch((error) => {
        console.error("Error loading persona settings:", error);
        this.showAdminStatus(
          `Error loading settings: ${error.message}`,
          "error",
          personaStatus
        );
      });
  },

  /**
   * Handles the submission of the persona settings form.
   * @param {Event} e - The form submission event.
   */
  handleSavePersona(e) {
    e.preventDefault(); // Prevent default form submission
    const {
      aiNameInput,
      aiRoleSelect,
      aiToneInput,
      aiCompanyInput,
      savePersonaBtn,
      personaStatus,
    } = this.Elements.admin;

    const personaData = {
      ai_name: aiNameInput.value.trim(),
      ai_role: aiRoleSelect.value,
      ai_tone: aiToneInput.value.trim(),
      company: aiCompanyInput.value.trim(),
    };

    this.showAdminStatus(
      "Saving persona settings...",
      "loading",
      personaStatus
    );
    savePersonaBtn.disabled = true;
    const originalButtonText = savePersonaBtn.innerHTML;
    savePersonaBtn.innerHTML =
      '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

    ApiService.savePersonaSettings(personaData)
      .then((updatedSettings) => {
        this.showAdminStatus(
          "Persona settings saved successfully!",
          "success",
          personaStatus
        );
        console.info("Persona settings saved:", updatedSettings);
        // Optionally re-populate form, though it should match
        aiNameInput.value = updatedSettings.ai_name;
        aiRoleSelect.value = updatedSettings.ai_role;
        aiToneInput.value = updatedSettings.ai_tone;
        aiCompanyInput.value = updatedSettings.company;
      })
      .catch((error) => {
        console.error("Error saving persona settings:", error);
        this.showAdminStatus(
          `Error saving settings: ${error.message}`,
          "error",
          personaStatus
        );
      })
      .finally(() => {
        // Restore button state
        savePersonaBtn.disabled = false;
        savePersonaBtn.innerHTML = originalButtonText;
      });
  },
};

export default AdminModule;
