console.log("HTML loaded. Waiting for JavaScript implementations.");

// --- DOM Elements ---
const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const chatForm = document.getElementById('chatForm');
const questionInput = document.getElementById('questionInput');
const sendButton = document.getElementById('sendButton');
const chatbox = document.getElementById('chatbox');
const loadingIndicator = document.getElementById('loadingIndicator');

let isDocumentProcessed = false; // Track if a document is ready for chat

// --- Functions ---
function addMessageToChatbox(message, sender) {
    // Clear the initial placeholder if it exists
    const placeholder = chatbox.querySelector('.text-center.text-muted');
    if (placeholder) {
        placeholder.remove();
    }

    const messageContainer = document.createElement('div');
    messageContainer.classList.add('message-container');

    const messageDiv = document.createElement('div'); // Div to hold the message bubble
    messageDiv.classList.add(sender === 'user' ? 'user-message' : 'bot-message');

    const bubbleDiv = document.createElement('div'); // The actual message bubble
    bubbleDiv.classList.add('message');
    bubbleDiv.textContent = message; // Use textContent for security

    messageDiv.appendChild(bubbleDiv);

    // Add Avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.classList.add('avatar');
    const avatarIcon = document.createElement('i');
    avatarIcon.classList.add('bi', sender === 'user' ? 'bi-person-fill' : 'bi-robot');
    avatarDiv.appendChild(avatarIcon);

    if (sender === 'user') {
            messageContainer.classList.add('user-message-container');
            messageContainer.appendChild(messageDiv); // Message first
            messageContainer.appendChild(avatarDiv);  // Avatar second
    } else {
            messageContainer.classList.add('bot-message-container');
            messageContainer.appendChild(avatarDiv);  // Avatar first
            messageContainer.appendChild(messageDiv); // Message second
    }

    // Hide loading indicator *before* adding new message
        if (sender === 'bot') {
            showLoading(false);
        }

    chatbox.appendChild(messageContainer);

    // Scroll to the bottom
    chatbox.scrollTop = chatbox.scrollHeight;
}

function showUploadStatus(message, type = 'info') {
    uploadStatus.innerHTML = ''; // Clear previous status
    const statusDiv = document.createElement('div');
    let iconClass = '';
    switch (type) {
        case 'success':
            statusDiv.className = 'alert alert-success alert-dismissible fade show small p-2 mb-0';
            iconClass = 'bi-check-circle-fill';
            break;
        case 'error':
            statusDiv.className = 'alert alert-danger alert-dismissible fade show small p-2 mb-0';
            iconClass = 'bi-exclamation-triangle-fill';
            break;
        case 'info':
        default:
            statusDiv.className = 'alert alert-info alert-dismissible fade show small p-2 mb-0';
            iconClass = 'bi-info-circle-fill';
            break;
        case 'loading':
                statusDiv.className = 'alert alert-warning small p-2 mb-0'; // Use warning color for loading
                iconClass = 'bi bi-hourglass-split'; // Hourglass icon
                message = `<div class="spinner-border spinner-border-sm me-2" role="status"><span class="visually-hidden">Loading...</span></div> ${message}`; // Add spinner
                statusDiv.innerHTML = message; // Set innerHTML directly for spinner
                uploadStatus.appendChild(statusDiv);
                return; // Skip adding icon and dismiss button for loading
    }

    statusDiv.setAttribute('role', 'alert');
    statusDiv.innerHTML = `
        <i class="bi ${iconClass} me-2"></i>
        ${message}
        <button type="button" class="btn-close p-2" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    uploadStatus.appendChild(statusDiv);
}

function enableChat(enable = true) {
    questionInput.disabled = !enable;
    sendButton.disabled = !enable;
    isDocumentProcessed = enable;
    if (enable) {
        questionInput.placeholder = "Ask a question about the document...";
    } else {
            questionInput.placeholder = "Upload a document first...";
    }
}

function showLoading(show = true) {
    if (loadingIndicator) {
        loadingIndicator.style.display = show ? 'flex' : 'none';
        if (show) {
            // Scroll down to show loading indicator if needed
            chatbox.scrollTop = chatbox.scrollHeight;
        }
    }
}

// --- Event Listeners ---
if (uploadForm) {
    uploadForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        console.log("Upload form submitted.");

        const file = fileInput.files[0];
        if (!file) {
            showUploadStatus("Please select a PDF file.", "error");
            return;
        }

        enableChat(false); // Disable chat during upload/processing
        showUploadStatus("Uploading and processing document...", "loading"); // Show loading status

        const formData = new FormData();
        formData.append('file', file);

        try {
            // !!! REPLACE WITH YOUR ACTUAL API ENDPOINT !!!
            const response = await fetch('/api/v1/upload', { 
                method: 'POST',
                body: formData,
                    // Add headers if required by your API (e.g., Authorization)
                    // headers: { 'Authorization': 'Bearer YOUR_TOKEN' }
            });

            // Get response body regardless of status for potential error messages
            const result = await response.json(); 

            if (response.ok) {
                console.log("Upload successful:", result);
                showUploadStatus(result.message || "Document processed successfully.", "success");
                enableChat(true); // Enable chat only on success
                // Optional: Clear chatbox or add a confirmation message from bot
                // chatbox.innerHTML = ''; // Clear previous chat
                // addMessageToChatbox("Your document is ready. Ask me anything!", "bot");

            } else {
                console.error("Upload failed:", result);
                // Try to get a specific error message from the API response
                const errorMessage = result.detail || result.error || `Server error: ${response.status}`;
                showUploadStatus(`Error: ${errorMessage}`, "error");
                enableChat(false); // Keep chat disabled on error
            }
        } catch (error) {
            console.error("Network or fetch error:", error);
            showUploadStatus("Upload failed. Check network connection or server status.", "error");
            enableChat(false); // Keep chat disabled on error
        } finally {
            // Optionally clear the file input after attempt
            // fileInput.value = ''; 
        }
    });
}

if (chatForm) {
    chatForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        console.log("Chat form submitted.");

        const question = questionInput.value.trim();
        if (question === '' || !isDocumentProcessed) {
                if (!isDocumentProcessed) {
                    // Maybe show a quick alert or feedback
                    alert("Please upload and process a document successfully first.");
                }
            return; // Don't send empty questions or if doc not ready
        }

        // Add user's question to chatbox immediately
        addMessageToChatbox(question, 'user');
        questionInput.value = ''; // Clear input field
        showLoading(true); // Show loading indicator while waiting for bot
        sendButton.disabled = true; // Disable send button while waiting
        questionInput.disabled = true; // Disable input field while waiting

        try {
            // !!! REPLACE WITH YOUR ACTUAL API ENDPOINT !!!
            const response = await fetch('/api/v1/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // Add other headers like Authorization if needed
                    // 'Authorization': 'Bearer YOUR_TOKEN'
                },
                body: JSON.stringify({ question: question }) 
            });

            const result = await response.json();

                if (response.ok) {
                console.log("Chat response received:", result);
                // Assuming the API returns the answer in a field named 'answer' or 'response'
                const answer = result.answer || result.response || "Sorry, I couldn't find an answer."; 
                addMessageToChatbox(answer, 'bot');
                } else {
                    console.error("Chat API error:", result);
                    const errorMessage = result.detail || result.error || `Server error: ${response.status}`;
                    addMessageToChatbox(`Error: ${errorMessage}`, 'bot'); // Show error in chat
                }

        } catch (error) {
            console.error("Network or fetch error during chat:", error);
            addMessageToChatbox("Sorry, I encountered a problem connecting to the assistant.", 'bot'); // Show network error in chat
        } finally {
                showLoading(false); // Hide loading indicator regardless of outcome
                // Re-enable chat input only if document is still considered processed
                if (isDocumentProcessed) {
                    sendButton.disabled = false;
                    questionInput.disabled = false;
                    questionInput.focus(); // Set focus back to input
                }
        }
    });
}

// --- Initial State ---
enableChat(false); // Start with chat disabled
showLoading(false); // Ensure loading is hidden initially
