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

export default AppState;
