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

async function respondApproval(id, approved, box) {
  box.querySelectorAll("button").forEach((b) => (b.disabled = true));
  const status = box.querySelector(".approval-status");
  try {
    await fetch("/api/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, approved }),
    });
    status.textContent = approved ? "已同意" : "已拒绝";
  } catch (err) {
    status.textContent = "提交失败: " + err.message;
  }
}

function addApprovalBubble(id, tool, args) {
  const box = document.createElement("div");
  box.className = "bubble approval";

  const label = document.createElement("div");
  label.className = "approval-label";
  label.textContent = `⚠️ 需要确认执行危险工具 ${tool}(${JSON.stringify(args)})`;

  const yes = document.createElement("button");
  yes.className = "yes";
  yes.textContent = "同意";
  yes.onclick = () => respondApproval(id, true, box);

  const no = document.createElement("button");
  no.className = "no";
  no.textContent = "拒绝";
  no.onclick = () => respondApproval(id, false, box);

  const status = document.createElement("div");
  status.className = "approval-status";

  box.append(label, yes, no, status);
  chat.appendChild(box);
  chat.scrollTop = chat.scrollHeight;
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
          } else if (ev.type === "approval_request") {
            addApprovalBubble(ev.id, ev.tool, ev.args);
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
