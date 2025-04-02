const API_BASE_URL = "/api/v1";

/**
 * Handles API response and error processing
 * @param {Response} response - Fetch API response object
 * @param {string} context - Context for logging (e.g., "Admin", "Chat")
 * @returns {Promise} - Promise that resolves to the parsed JSON or rejects with an error
 */
async function handleResponse(response, context) {
  console.log(`${context}: Fetch response received:`, response.status);

  if (!response.ok) {
    try {
      const errData = await response.json();
      console.error(`${context}: Backend error response:`, errData);
      throw new Error(
        errData.detail || `HTTP error! status: ${response.status}`
      );
    } catch (jsonError) {
      console.error(
        `${context}: Failed to parse backend error JSON or generic HTTP error:`,
        jsonError
      );
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  }

  // For 204 No Content responses
  if (response.status === 204) {
    return null;
  }

  return response.json();
}

const ApiService = {
  /**
   * Upload a file to the server
   * @param {File} file - The file to upload
   * @returns {Promise} - Promise that resolves to the upload result
   */
  uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    return fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    }).then((response) => handleResponse(response, "Admin"));
  },

  /**
   * Delete a context file from the server
   * @param {string} filename - The filename to delete
   * @returns {Promise} - Promise that resolves when deletion is complete
   */
  deleteContext(filename) {
    return fetch(
      `${API_BASE_URL}/delete_context/${encodeURIComponent(filename)}`,
      {
        method: "DELETE",
      }
    ).then((response) => handleResponse(response, "Admin"));
  },

  /**
   * Send a chat message and get a response
   * @param {string} question - The user's question
   * @param {Array} chatHistory - Array of previous chat messages
   * @returns {Promise} - Promise that resolves to the chat response
   */
  sendChatMessage(question, chatHistory) {
    const payload = {
      question: question,
      chat_history: chatHistory,
    };

    return fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then((response) => handleResponse(response, "Customer"));
  },

  /**
   * Get the list of available documents (if you need this endpoint)
   * @returns {Promise} - Promise that resolves to the list of documents
   */
  getDocuments() {
    return fetch(`${API_BASE_URL}/documents`).then((response) =>
      handleResponse(response, "Admin")
    );
  },

  /**
   * Send an admin test question to get context preview
   * @param {string} question - The admin's test question
   * @returns {Promise} - Promise that resolves to the preview response {retrieved_chunks, draft_answer}
   */
  getAdminPreview(question) {
    const payload = {
      question: question,
    };

    return fetch(`${API_BASE_URL}/admin/preview_context`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then((response) => handleResponse(response, "Admin Preview"));
  },
};

export default ApiService;
