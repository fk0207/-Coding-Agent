const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("message");

function addBubble(text, cls) {
  const div = document.createElement("div");
  div.className = "bubble " + cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  addBubble(message, "user");
  input.value = "";

  let answerBubble = null;
  let answer = "";

  try {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok || !res.body) throw new Error("HTTP " + res.status);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      let sep;
      while ((sep = buf.indexOf("\n\n")) !== -1) {
        const raw = buf.slice(0, sep);
        buf = buf.slice(sep + 2);
        for (const line of raw.split("\n")) {
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          const ev = JSON.parse(payload);

          if (ev.type === "delta") {
            answer += ev.content;
            if (!answerBubble) answerBubble = addBubble(answer, "assistant");
            else answerBubble.textContent = answer;
          } else if (ev.type === "tool") {
            addBubble(`🛠 ${ev.tool}(${JSON.stringify(ev.args)})\n→ ${ev.result}`, "trace");
          } else if (ev.type === "done") {
            if (!answer && ev.answer) answer = ev.answer;
          }
        }
      }
    }

    if (answerBubble) answerBubble.textContent = answer || "(无输出)";
    else addBubble(answer || "(无输出)", "assistant");
  } catch (err) {
    if (answerBubble) answerBubble.textContent = "请求失败: " + err.message;
    else addBubble("请求失败: " + err.message, "assistant");
  }
  chat.scrollTop = chat.scrollHeight;
});
