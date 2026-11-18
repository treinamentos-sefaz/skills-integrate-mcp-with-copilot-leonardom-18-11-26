document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupContainer = document.getElementById("signup-container");
  const emailInput = document.getElementById("email");
  const messageDiv = document.getElementById("message");
  const authForm = document.getElementById("auth-form");
  const authSession = document.getElementById("auth-session");
  const authMessage = document.getElementById("auth-message");
  const tokenInput = document.getElementById("token");
  let token = null;
  let account = null;

  function showMessage(element, message, type) {
    element.textContent = message;
    element.className = type;
  }

  function signOut() {
    token = null;
    account = null;
    tokenInput.value = "";
    emailInput.value = "";
    emailInput.readOnly = false;
    authForm.classList.remove("hidden");
    authSession.classList.add("hidden");
    signupContainer.classList.add("hidden");
    messageDiv.classList.add("hidden");
    fetchActivities();
  }

  authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/auth/me", {
        headers: { Authorization: `Bearer ${tokenInput.value}` },
      });
      const result = await response.json();
      if (!response.ok) {
        showMessage(authMessage, result.detail || "Sign in failed", "error");
        return;
      }
      token = tokenInput.value;
      account = result;
      tokenInput.value = "";
      authForm.classList.add("hidden");
      authSession.classList.remove("hidden");
      signupContainer.classList.remove("hidden");
      document.getElementById("auth-identity").textContent =
        `Signed in as ${account.email} (${account.role})`;
      authMessage.textContent = "";
      authMessage.className = "";
      emailInput.value = account.role === "student" ? account.email : "";
      emailInput.readOnly = account.role === "student";
      await fetchActivities();
    } catch (error) {
      showMessage(authMessage, "Sign in failed. Please try again.", "error");
      console.error("Error signing in:", error);
    }
  });

  document.getElementById("logout").addEventListener("click", signOut);

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const activities = await response.json();
      activitiesList.replaceChildren();
      const selectedActivity = activitySelect.value;
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const card = document.createElement("div");
        card.className = "activity-card";
        const heading = document.createElement("h4");
        heading.textContent = name;
        card.appendChild(heading);
        for (const text of [
          details.description,
          `Schedule: ${details.schedule}`,
          `Availability: ${details.max_participants - details.participants.length} spots left`,
        ]) {
          const paragraph = document.createElement("p");
          paragraph.textContent = text;
          card.appendChild(paragraph);
        }

        const participants = document.createElement("div");
        participants.className = "participants-section";
        if (details.participants.length === 0) {
          participants.textContent = "No participants yet";
        } else {
          const title = document.createElement("h5");
          title.textContent = "Participants:";
          const list = document.createElement("ul");
          list.className = "participants-list";
          details.participants.forEach((email) => {
            const item = document.createElement("li");
            const label = document.createElement("span");
            label.className = "participant-email";
            label.textContent = email;
            item.appendChild(label);
            if (account && (account.role === "admin" ||
                account.email.toLowerCase() === email.toLowerCase())) {
              const button = document.createElement("button");
              button.className = "delete-btn";
              button.type = "button";
              button.textContent = "❌";
              button.setAttribute("aria-label", `Unregister ${email}`);
              button.addEventListener("click", () => unregister(name, email));
              item.appendChild(button);
            }
            list.appendChild(item);
          });
          participants.append(title, list);
        }
        card.appendChild(participants);
        activitiesList.appendChild(card);
        activitySelect.add(new Option(name, name));
      });
      activitySelect.value = selectedActivity;
    } catch (error) {
      activitiesList.textContent = "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  async function changeRegistration(activity, email, action, method) {
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/${action}?email=${encodeURIComponent(email)}`,
        { method, headers: { Authorization: `Bearer ${token}` } }
      );
      const result = await response.json();
      showMessage(messageDiv, response.ok ? result.message : result.detail || "An error occurred",
        response.ok ? "success" : "error");
      if (response.ok) await fetchActivities();
    } catch (error) {
      showMessage(messageDiv, "Request failed. Please try again.", "error");
      console.error("Error changing registration:", error);
    }
  }

  function unregister(activity, email) {
    changeRegistration(activity, email, "unregister", "DELETE");
  }

  signupForm.addEventListener("submit", (event) => {
    event.preventDefault();
    changeRegistration(activitySelect.value, emailInput.value, "signup", "POST");
  });

  fetchActivities();
});
