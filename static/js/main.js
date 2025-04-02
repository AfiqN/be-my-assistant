import AppState from "./modules/appState.js";
import Elements from "./modules/elements.js";
import ViewManager from "./modules/viewManager.js";
import AdminModule from "./modules/adminModule.js";
import ChatModule from "./modules/chatModule.js";

document.addEventListener("DOMContentLoaded", function () {
  // Initialize AOS animations
  AOS.init({
    duration: 800,
    once: true,
  });

  // Initialize modules
  ViewManager.init(AppState, Elements);
  AdminModule.init(AppState, Elements);
  ChatModule.init(AppState, Elements);
});
