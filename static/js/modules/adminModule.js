import { escapeHTML, formatFileSize } from "/static/js/utils.js";
import ApiService from "./apiService.js";

const AdminModule = {
  init(AppState, Elements) {
    this.AppState = AppState;
    this.Elements = Elements;
    this.initAdminFileUpload();
  },

  initAdminFileUpload() {
    const { uploadForm, fileInput, browseBtn, uploadBtn } = this.Elements.admin;

    if (!uploadForm) {
      console.warn(
        "Admin upload form not found. Skipping admin event listeners."
      );
      return;
    }

    // File input handling
    fileInput.addEventListener("change", () => this.handleFileSelection());
    browseBtn.addEventListener("click", () => fileInput.click());

    // File drop area
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

    // Form submission
    uploadForm.addEventListener("submit", (e) => this.handleUploadSubmit(e));

    // Initial UI state
    this.updateDocumentList();
    uploadBtn.disabled = true;
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

    console.log("Admin: handleFileSelection triggered.");

    if (fileInput.files.length > 0) {
      const file = fileInput.files[0];
      console.log("Admin: File selected:", file.name, file.type);

      const allowedTypes = [
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", // .docx
        "text/markdown",
        "text/x-markdown", // Some systems use this for .md
      ];

      const fileExtension = file.name.split(".").pop().toLowerCase();
      const allowedExtensions = ["pdf", "txt", "docx", "md"];

      if (
        !allowedTypes.includes(file.type) &&
        !allowedExtensions.includes(fileExtension)
      ) {
        console.log(
          "Admin: Invalid file type or extension.",
          file.type,
          fileExtension
        );
        this.showAdminStatus(
          "Please upload a supported document (PDF, TXT, DOCX, MD).",
          "error"
        );
        fileInput.value = ""; // Clear the input
        selectedFileDiv.innerHTML = "";
        selectedFileDiv.style.display = "none";
        this.AppState.admin.currentFile = null;
        uploadBtn.disabled = true;
        return;
      }

      this.AppState.admin.currentFile = file;
      selectedFileDiv.innerHTML = `
          <i class="bi bi-file-earmark-text-fil"></i> 
          ${escapeHTML(file.name)} (${formatFileSize(file.size)})
        `;
      selectedFileDiv.style.display = "flex";
      uploadBtn.disabled = false;
      this.showAdminStatus("", "clear");
      console.log(
        "Admin: Valid file selected. currentFile set to:",
        this.AppState.admin.currentFile
      );
    } else {
      console.log("Admin: No file selected in input.");
      selectedFileDiv.innerHTML = "";
      selectedFileDiv.style.display = "none";
      this.AppState.admin.currentFile = null;
      uploadBtn.disabled = true;
    }
  },

  handleUploadSubmit(e) {
    e.preventDefault();

    const { uploadBtn, fileInput } = this.Elements.admin;

    console.log("Admin: Upload form submitted.");

    if (!this.AppState.admin.currentFile) {
      console.log("Admin: currentFile is null or empty.");
      this.showAdminStatus("Please select a PDF file first.", "error");
      return;
    }

    if (this.AppState.admin.isUploading) {
      console.log("Admin: Upload already in progress.");
      return;
    }

    this.AppState.admin.isUploading = true;
    this.showAdminStatus(
      '<div class="spinner-border spinner-border-sm me-2" role="status"></div> Processing document...',
      "loading"
    );
    uploadBtn.disabled = true;
    fileInput.disabled = true;

    ApiService.uploadFile(this.AppState.admin.currentFile)
      .then((data) => {
        console.log("Admin: Upload successful. Backend data:", data);
        this.showAdminStatus(
          `
          <i class="bi bi-check-circle"></i> 
          ${data.message || "Context successfully processed!"} 
          (${data.chunks_added} sections added)
        `,
          "success"
        );

        // Add to processed files list
        this.AppState.admin.processedFiles.push(data.filename);
        this.updateDocumentList();

        // Reset file input
        fileInput.value = "";
        this.Elements.admin.selectedFileDiv.innerHTML = "";
        this.Elements.admin.selectedFileDiv.style.display = "none";
        this.AppState.admin.currentFile = null;
      })
      .catch((error) => {
        console.error("Admin: Upload Fetch Error:", error);
        this.showAdminStatus(
          `<i class="bi bi-exclamation-triangle"></i> Error: ${error.message}`,
          "error"
        );
      })
      .finally(() => {
        console.log("Admin: Fetch finished. Re-enabling buttons.");
        this.AppState.admin.isUploading = false;
        uploadBtn.disabled = false;
        fileInput.disabled = false;
        this.handleFileSelection();
      });
  },

  showAdminStatus(message, type) {
    const { uploadStatus } = this.Elements.admin;

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
  },

  updateDocumentList() {
    const { documentList } = this.Elements.admin;

    if (!documentList) return;

    documentList.innerHTML = "";

    if (this.AppState.admin.processedFiles.length === 0) {
      documentList.innerHTML =
        '<li class="list-group-item text-muted"><em>No processed documents yet.</em></li>';
    } else {
      this.AppState.admin.processedFiles.forEach((filename) => {
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
      const self = this;
      documentList.querySelectorAll(".delete-doc-btn").forEach((btn) => {
        btn.addEventListener("click", function () {
          const filenameToDelete = this.getAttribute("data-filename");
          const buttonElement = this; // Keep reference to the button

          // Disable button immediately
          buttonElement.disabled = true;
          buttonElement.innerHTML =
            '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

          console.log(`Attempting to delete context for: ${filenameToDelete}`);

          ApiService.deleteContext(filenameToDelete)
            .then(() => {
              // --- Success: Update frontend state and UI ---
              self.AppState.admin.processedFiles =
                self.AppState.admin.processedFiles.filter(
                  (f) => f !== filenameToDelete
                );
              self.updateDocumentList(); // Re-render the list which will remove the item
              self.showAdminStatus(
                `<i class="bi bi-check-circle"></i> Context "${escapeHTML(
                  filenameToDelete
                )}" removed successfully.`,
                "success"
              );
            })
            .catch((error) => {
              // --- Failure: Show error and re-enable button ---
              console.error("Error deleting context:", error);
              self.showAdminStatus(
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
  },
};

export default AdminModule;
