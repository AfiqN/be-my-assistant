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
    // Upload elements
    uploadForm: document.getElementById("uploadForm"),
    fileInput: document.getElementById("fileInput"),
    browseBtn: document.getElementById("browseBtn"),
    selectedFileDiv: document.getElementById("selectedFile"),
    uploadBtn: document.getElementById("uploadBtn"),
    uploadStatus: document.getElementById("uploadStatus"),
    documentList: document.getElementById("documentList"),

    // Preview elements
    previewForm: document.getElementById("previewForm"),
    previewQuestionInput: document.getElementById("previewQuestionInput"),
    previewSubmitBtn: document.getElementById("previewSubmitBtn"),
    previewSpinner: document.getElementById("previewSpinner"),
    previewResults: document.getElementById("previewResults"),
    retrievedChunksList: document.getElementById("retrievedChunksList"),
    draftAnswer: document.getElementById("draftAnswer"),
    previewStatus: document.getElementById("previewStatus"),

    personaForm: document.getElementById("personaForm"),
    aiNameInput: document.getElementById("aiNameInput"),
    aiRoleSelect: document.getElementById("aiRoleSelect"),
    aiToneInput: document.getElementById("aiToneInput"),
    aiCompanyInput: document.getElementById("aiCompanyInput"),
    savePersonaBtn: document.getElementById("savePersonaBtn"),
    personaStatus: document.getElementById("personaStatus"), // Div for status messages
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

export default Elements;
