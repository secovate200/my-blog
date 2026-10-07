(() => {
    const csrfToken = () => document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || "";
    const post = async (url, data = {}) => {
        const response = await fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-CSRFToken": csrfToken()},
            body: new URLSearchParams(data),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "요청을 처리하지 못했습니다.");
        return payload;
    };
    const createMemberRow = (membership) => {
        const row = document.createElement("li");
        row.className = "project-member-row";
        row.dataset.membershipId = membership.id;
        const identity = document.createElement("div");
        const username = document.createElement("strong");
        username.textContent = membership.username;
        identity.append(username);
        if (membership.email) {
            const email = document.createElement("span");
            email.textContent = membership.email;
            identity.append(email);
        }
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn-small";
        remove.dataset.memberRemove = "";
        remove.dataset.removeUrl = membership.remove_url;
        remove.textContent = "제거";
        row.append(identity, remove);
        return row;
    };
    const initializeManager = (manager) => {
        if (manager.dataset.initialized) return;
        manager.dataset.initialized = "true";
        const list = manager.querySelector("[data-member-list]");
        const empty = manager.querySelector("[data-member-empty]");
        list.addEventListener("click", async (event) => {
            const button = event.target.closest("[data-member-remove]");
            if (!button) return;
            button.disabled = true;
            try {
                await post(button.dataset.removeUrl);
                button.closest("[data-membership-id]").remove();
                empty.classList.toggle("hidden", list.children.length > 0);
            } catch (error) {
                window.alert(error.message);
                button.disabled = false;
            }
        });
    };
    const initializePopup = (popup) => {
        if (popup.dataset.initialized) return;
        popup.dataset.initialized = "true";
        const input = popup.querySelector("input[type='search']");
        const searchButton = popup.querySelector("[data-member-search-button]");
        const status = popup.querySelector("[data-member-search-status]");
        const results = popup.querySelector("[data-member-search-results]");
        const search = async () => {
            const query = input.value.trim();
            results.replaceChildren();
            if (!query) {
                status.textContent = "사용자 이름 또는 이메일을 입력하세요.";
                return;
            }
            status.textContent = "검색 중...";
            const url = new URL(popup.dataset.searchUrl, window.location.origin);
            url.searchParams.set("q", query);
            try {
                const response = await fetch(url);
                const payload = await response.json();
                if (!response.ok) throw new Error(payload.error || "검색하지 못했습니다.");
                status.textContent = payload.users.length ? `${payload.users.length}명의 사용자를 찾았습니다.` : "추가할 수 있는 사용자가 없습니다.";
                payload.users.forEach((user) => {
                    const item = document.createElement("li");
                    item.className = "project-member-result";
                    const identity = document.createElement("div");
                    const username = document.createElement("strong");
                    username.textContent = user.username;
                    identity.append(username);
                    if (user.email) {
                        const email = document.createElement("span");
                        email.textContent = user.email;
                        identity.append(email);
                    }
                    const add = document.createElement("button");
                    add.type = "button";
                    add.className = "btn btn-primary btn-small";
                    add.textContent = "추가";
                    add.addEventListener("click", async () => {
                        add.disabled = true;
                        try {
                            const payload = await post(popup.dataset.addUrl, {user_id: user.id});
                            const manager = document.querySelector(`[data-project-member-manager][data-project-id="${popup.dataset.projectId}"]`);
                            if (payload.created && manager) {
                                manager.querySelector("[data-member-list]").append(createMemberRow(payload.membership));
                                manager.querySelector("[data-member-empty]").classList.add("hidden");
                            }
                            bootstrap5.Modal.getInstance(document.getElementById("sb-admin-modal"))?.hide();
                        } catch (error) {
                            status.textContent = error.message;
                            add.disabled = false;
                        }
                    });
                    item.append(identity, add);
                    results.append(item);
                });
            } catch (error) {
                status.textContent = error.message;
            }
        };
        searchButton.addEventListener("click", search);
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                search();
            }
        });
        input.focus();
    };
    const initialize = () => {
        document.querySelectorAll("[data-project-member-manager]").forEach(initializeManager);
        document.querySelectorAll("[data-project-member-popup]").forEach(initializePopup);
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize, {once: true});
    else initialize();
    document.body.addEventListener("htmx:afterSwap", initialize);
    document.body.addEventListener("SBModalShown", initialize);
})();
