export function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " bytes";
  else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  else return (bytes / 1048576).toFixed(1) + " MB";
}

export function escapeHTML(str) {
  if (typeof str !== "string") return "";
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

export function scrollToBottom(chatbox) {
  if (chatbox) {
    chatbox.scrollTop = chatbox.scrollHeight;
  }
}
