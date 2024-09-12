function showNotification(message, type = "success") {
  const notification = document.createElement("div");
  notification.className = `notification ${type}`;
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.classList.add("hidden");
    setTimeout(() => {
      notification.remove();
    }, 500);
  }, 3000);
}
