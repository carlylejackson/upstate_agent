(function () {
  var API_BASE = window.UPSTATE_AGENT_API_BASE || "https://your-api-domain.example.com";
  var sessionId = null;

  function createWidget() {
    var container = document.createElement("div");
    container.id = "upstate-agent-widget";
    container.style.cssText = "position:fixed;bottom:20px;right:20px;width:320px;background:#fff;border:1px solid #ccc;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.15);font-family:Arial,sans-serif;z-index:99999;";

    container.innerHTML = "<div style='padding:12px;border-bottom:1px solid #eee;font-weight:700'>Upstate Support</div>"
      + "<div id='upstate-agent-log' style='height:280px;overflow:auto;padding:12px;font-size:14px;'></div>"
      + "<div style='padding:12px;border-top:1px solid #eee'>"
      + "<input id='upstate-agent-input' placeholder='Type your question...' style='width:100%;padding:8px;box-sizing:border-box'/>"
      + "</div>";
    document.body.appendChild(container);

    var input = document.getElementById("upstate-agent-input");
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        sendMessage(input.value);
        input.value = "";
      }
    });
  }

  function append(role, text) {
    var log = document.getElementById("upstate-agent-log");
    var row = document.createElement("div");
    row.style.marginBottom = "8px";
    row.innerHTML = "<strong>" + role + ":</strong> " + text;
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }

  async function ensureSession() {
    if (sessionId) return;
    var res = await fetch(API_BASE + "/v1/chat/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel: "web", consent_to_contact: false })
    });
    var json = await res.json();
    sessionId = json.session_id;
  }

  async function sendMessage(text) {
    if (!text) return;
    append("You", text);
    await ensureSession();
    var res = await fetch(API_BASE + "/v1/chat/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, channel: "web", text: text })
    });
    var json = await res.json();
    append("Agent", json.response_text || "Sorry, something went wrong.");
  }

  createWidget();
})();
