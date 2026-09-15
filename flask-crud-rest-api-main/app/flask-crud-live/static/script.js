const form = document.getElementById('userForm');
const usersContainer = document.getElementById('users');
const message = document.getElementById('message');

form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();

    try {
        const response = await fetch('/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email })
        });

        const data = await response.json();
        message.textContent = data.message;

        if (response.ok) {
            form.reset();
            loadUsers();
        }
    } catch (error) {
        message.textContent = 'Unable to connect to the server.';
    }
});

async function loadUsers() {
    usersContainer.innerHTML = '<p>Loading...</p>';

    try {
        const response = await fetch('/users');
        const users = await response.json();

        if (!response.ok || !Array.isArray(users)) {
            usersContainer.innerHTML = '<p>Unable to load users.</p>';
            return;
        }

        if (users.length === 0) {
            usersContainer.innerHTML = '<p>No users found.</p>';
            return;
        }

        usersContainer.innerHTML = users.map(user => `
            <div class="user">
                <div class="user-info">
                    <strong>${escapeHtml(user.username)}</strong>
                    <span>${escapeHtml(user.email)}</span>
                </div>
                <button class="delete-btn" onclick="deleteUser(${user.id})">Delete</button>
            </div>
        `).join('');
    } catch (error) {
        usersContainer.innerHTML = '<p>Unable to connect to the server.</p>';
    }
}

async function deleteUser(id) {
    if (!confirm('Delete this user?')) {
        return;
    }

    try {
        const response = await fetch(`/users/${id}`, {
            method: 'DELETE'
        });

        const data = await response.json();
        message.textContent = data.message;
        loadUsers();
    } catch (error) {
        message.textContent = 'Unable to connect to the server.';
    }
}

function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value;
    return div.innerHTML;
}

loadUsers();
