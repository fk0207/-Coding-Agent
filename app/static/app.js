const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("message");

function addBubble(text, cls) {
  const div = document.createElement("div");
  div.className = "bubble " + cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  addBubble(message, "user");
  input.value = "";
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    if (data.trace && data.trace.length) {
      data.trace.forEach((t) =>
        addBubble(`🛠 ${t.tool}(${JSON.stringify(t.args)})\n→ ${t.result}`, "trace")
      );
    }
    addBubble(data.answer, "assistant");
  } catch (err) {
    addBubble("请求失败: " + err.message, "assistant");
  }
});
