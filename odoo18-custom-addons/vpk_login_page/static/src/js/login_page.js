/* VPK login page: password visibility toggle + link placement */
(function () {
    "use strict";

    function buildToggle(input) {
        if (!input || input.closest(".vpk-password-field")) {
            return;
        }
        const wrapper = document.createElement("div");
        wrapper.className = "vpk-password-field";
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const button = document.createElement("button");
        button.type = "button";
        button.className = "vpk-password-toggle";
        button.setAttribute("aria-label", "แสดง/ซ่อนรหัสผ่าน");
        button.innerHTML = '<i class="fa fa-eye" aria-hidden="true"></i>';
        wrapper.appendChild(button);

        button.addEventListener("click", function () {
            const hidden = input.getAttribute("type") === "password";
            input.setAttribute("type", hidden ? "text" : "password");
            button.innerHTML = hidden
                ? '<i class="fa fa-eye-slash" aria-hidden="true"></i>'
                : '<i class="fa fa-eye" aria-hidden="true"></i>';
            input.focus();
        });
    }

    function moveResetLink(form) {
        const label = form.querySelector("label[for='password']");
        const link = label && label.querySelector("a");
        if (!link) {
            return;
        }
        const group = label.closest(".mb-3");
        if (!group || group.querySelector(".vpk-login-forgot")) {
            return;
        }
        const holder = document.createElement("div");
        holder.className = "vpk-login-forgot";
        holder.appendChild(link);
        group.appendChild(holder);
    }

    function bindTestUsers(form) {
        const select = form.querySelector(".vpk-login-test-select");
        const login = form.querySelector("input#login");
        const password = form.querySelector("input#password");
        if (!select || !login) {
            return;
        }
        if (login.value) {
            select.value = login.value;
        }
        select.addEventListener("change", function () {
            if (!select.value) {
                return;
            }
            login.value = select.value;
            if (password) {
                const option = select.options[select.selectedIndex];
                password.value = (option && option.dataset.password) || "";
                const submit = form.querySelector("button[type='submit']");
                if (password.value && submit) {
                    submit.focus();
                } else {
                    password.focus();
                }
            }
        });
    }

    function enhance() {
        const panel = document.querySelector(".vpk-login-panel");
        if (!panel) {
            return;
        }
        panel.querySelectorAll("form").forEach(function (form) {
            moveResetLink(form);
            bindTestUsers(form);
            form.querySelectorAll("input[type='password']").forEach(buildToggle);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", enhance);
    } else {
        enhance();
    }
})();
