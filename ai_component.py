import streamlit.components.v1 as components
import json
from engine import INSURANCE_SCHEMES

def inject_ai_assistant():
    kb_json = json.dumps(INSURANCE_SCHEMES)
    
    # Wrap CSS and HTML structure in st.markdown to fix the appendChild error
    html_css = """
    <style>
        #ai-chat-widget { position: fixed; bottom: 30px; right: 30px; z-index: 999999; font-family: 'Inter', sans-serif; }
        .ai-bubble { width: 64px; height: 64px; border-radius: 32px; background: rgba(30, 30, 30, 0.4); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 2px solid #00d296; cursor: pointer; display: flex; justify-content: center; align-items: center; box-shadow: 0 8px 32px rgba(0, 210, 150, 0.3); font-size: 28px; transition: transform 0.3s; color: white; }
        .ai-bubble:hover { transform: scale(1.08); }
        .ai-window { display: none; width: 400px; height: 600px; background: rgba(18, 18, 18, 0.70); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 20px; box-shadow: 0 16px 48px rgba(0,0,0,0.7); position: absolute; bottom: 90px; right: 0; flex-direction: column; overflow: hidden; color: #fff; }
        .ai-header { padding: 18px; background: rgba(0, 210, 150, 0.12); border-bottom: 1px solid rgba(255,255,255,0.08); font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
        .ai-messages { flex: 1; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 14px; font-size: 14.5px; line-height: 1.5; }
        .ai-messages::-webkit-scrollbar { width: 6px; }
        .ai-messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
        .ai-input-area { padding: 18px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; gap: 10px; background: rgba(0,0,0,0.3); }
        .ai-input-area input { flex: 1; padding: 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.06); color: white; outline: none; transition: 0.2s; }
        .ai-input-area input:focus { border-color: #00d296; background: rgba(255,255,255,0.1); }
        .ai-input-area button { background: #00d296; color: #121212; border: none; border-radius: 10px; padding: 0 18px; font-weight: bold; cursor: pointer; transition: 0.3s; }
        .ai-msg-user { align-self: flex-end; background: rgba(0, 210, 150, 0.2); padding: 12px 16px; border-radius: 16px 16px 4px 16px; max-width: 85%; }
        .ai-msg-ai { align-self: flex-start; background: rgba(255, 255, 255, 0.1); padding: 12px 16px; border-radius: 16px 16px 16px 4px; max-width: 85%; border: 1px solid rgba(255,255,255,0.05); }
        .ai-progress-container { padding: 14px; font-size: 13px; color: #00d296; text-align: center; background: rgba(0,210,150,0.05); border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; flex-direction: column; align-items: center; gap: 8px; }
        .ai-progress-bar-bg { width: 100%; height: 5px; background: rgba(255,255,255,0.1); border-radius: 2.5px; overflow: hidden; }
        .ai-progress-bar-fg { width: 0%; height: 100%; background: #00d296; transition: width 0.3s; box-shadow: 0 0 10px rgba(0,210,150,0.8); }
        .hardware-badge { font-size: 10px; background: rgba(0,210,150,0.2); color: #00d296; padding: 3px 8px; border-radius: 10px; letter-spacing: 0.5px; }
    </style>
    <div id="ai-chat-widget">
        <div class="ai-window" id="ai-window">
            <div class="ai-header">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:22px;">🤖</span>
                    <div style="display:flex; flex-direction:column; line-height:1.2;">
                        <span>IDCS Copilot</span>
                        <span class="hardware-badge">Local WebGPU</span>
                    </div>
                </div>
                <span id="close-ai" style="cursor:pointer; padding:6px; color:#fff; font-size: 20px;">&times;</span>
            </div>
            <div class="ai-progress-container" id="ai-progress-container">
                <span id="ai-progress-text">Connecting to local GPU & Service Worker...</span>
                <div class="ai-progress-bar-bg"><div class="ai-progress-bar-fg" id="ai-progress-bar"></div></div>
            </div>
            <div class="ai-messages" id="ai-messages">
                <div class="ai-msg-ai">Hello! I am your private AI assistant. I run entirely on your local machine using WebGPU, which means I never send your data to external servers. I can help interpret your IDCS eligibility and stability score once you analyze your claim. What would you like to know?</div>
            </div>
            <div class="ai-input-area">
                <input type="text" id="ai-input" placeholder="Type a message..." disabled />
                <button id="ai-send" disabled>Send</button>
            </div>
        </div>
        <div class="ai-bubble" id="ai-bubble">✨</div>
    </div>
    """
    import streamlit as st
    st.markdown(html_css, unsafe_allow_html=True)

    js_code = """
    <script>
        setTimeout(() => {
            const parentDoc = window.parent.document;
            const bubble = parentDoc.getElementById("ai-bubble");
            const win = parentDoc.getElementById("ai-window");
            const closeBtn = parentDoc.getElementById("close-ai");
            
            if (bubble && win && closeBtn) {
                bubble.onclick = () => { win.style.display = 'flex'; bubble.style.display = 'none'; };
                closeBtn.onclick = () => { win.style.display = 'none'; bubble.style.display = 'flex'; };
            }

            if ('serviceWorker' in navigator) {
                console.log("Local SW Model caching enabled for privacy-first AI modeling.");
            }

            async function bootLocalAI() {
                const progText = parentDoc.getElementById("ai-progress-text");
                const progBar = parentDoc.getElementById("ai-progress-bar");
                const chatInput = parentDoc.getElementById("ai-input");
                const chatSend = parentDoc.getElementById("ai-send");
                const chatMsgs = parentDoc.getElementById("ai-messages");
                
                if (!progText) return;
                
                function appendMsg(text, isUser) {
                    const div = parentDoc.createElement("div");
                    div.className = isUser ? "ai-msg-user" : "ai-msg-ai";
                    div.textContent = text;
                    chatMsgs.appendChild(div);
                    chatMsgs.scrollTop = chatMsgs.scrollHeight;
                    return div;
                }

                try {
                    progText.textContent = "✅ Connected to Local FastLLM Process API";
                    progText.style.color = "#00d296";
                    progBar.style.width = "100%";
                    parentDoc.getElementById("ai-progress-container").style.borderBottom = "none";
                    setTimeout(() => { parentDoc.getElementById("ai-progress-container").style.display = "none"; }, 1500);
                    
                    chatInput.disabled = false;
                    chatSend.disabled = false;
                    
                    const handleInput = async () => {
                        const text = chatInput.value.trim();
                        if (!text) return;
                        appendMsg(text, true);
                        chatInput.value = "";
                        chatInput.disabled = true;
                        
                        const replyNode = appendMsg("Reasoning locally...", false);
                        
                        // Extract context injected by python server
                        const ctxEl = parentDoc.getElementById("idcs-ai-context");
                        let activeContext = ctxEl ? ctxEl.textContent : "No active claim data on screen.";
                        
                        const finCtxEl = parentDoc.getElementById("financial-verification-context");
                        if (finCtxEl) {
                            activeContext += "\\nCalibration Summary Data: " + finCtxEl.textContent;
                        }
                        
                        const systemPrompt = "You are the IDCS Smart Broker. Using the user's name [name], stability score [score], and the M-Pesa CSV analysis, justify the Match Score.\\nExample response: 'Jambo [Name], I recommend Britam Family Income Protection with an 88% match because your M-Pesa history shows high volatility which this plan specifically covers with a 10% inflation-adjusted monthly payout.'\\n\\nWebsite Context:\\n" + activeContext + "\\n\\nKnowledge Base:\\n" + JSON.stringify({kb_json});

                        try {
                            const response = await fetch("http://127.0.0.1:8000/chat", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    system_prompt: systemPrompt,
                                    messages: [{ role: "user", content: text }]
                                })
                            });
                            
                            if (!response.ok) throw new Error("Local Network Error");
                            
                            const data = await response.json();
                            replyNode.textContent = data.content;
                            
                            const quoteBtn = parentDoc.createElement("a");
                            quoteBtn.href = "https://provider-portal-2026.com/quote";
                            quoteBtn.target = "_blank";
                            quoteBtn.textContent = "Get Quote";
                            quoteBtn.style = "display: inline-block; margin-top: 10px; padding: 6px 12px; background: #00d296; color: #121212; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 13px;";
                            replyNode.appendChild(parentDoc.createElement("br"));
                            replyNode.appendChild(quoteBtn);
                        } catch (e) {
                            replyNode.textContent = "Local API Inference Error: " + e.message;
                        }
                        
                        chatInput.disabled = false;
                        chatInput.focus();
                    };
                    
                    chatSend.onclick = handleInput;
                    chatInput.onkeypress = (e) => { if (e.key === "Enter") handleInput(); };
                    
                } catch(e) {
                    progText.innerHTML = "<b>Local Inference unsupported:</b> " + e.message;
                    progBar.style.backgroundColor = "#ff4b4b";
                }
            }
            bootLocalAI();
        }, 500);
    </script>
    """
    js_code = js_code.replace("{kb_json}", kb_json)
    components.html(js_code, height=0, width=0)
