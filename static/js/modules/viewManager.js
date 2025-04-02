const ViewManager = {
  init(AppState, Elements) {
    // Set initial view
    this.switchView(AppState.currentView, AppState, Elements);

    // Add event listeners for view switching
    Elements.nav.adminBtn.addEventListener("click", () =>
      this.switchView("admin-view", AppState, Elements)
    );
    Elements.nav.customerBtn.addEventListener("click", () =>
      this.switchView("customer-view", AppState, Elements)
    );
    Elements.nav.aboutBtn.addEventListener("click", (e) => {
      e.preventDefault();
      Elements.modal.about.show();
    });
  },

  switchView(viewId, AppState, Elements) {
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
  },
};

export default ViewManager;
