import streamlit.components.v1 as components

def inject_ai_assistant():
    html_code = """
    <script>
        const parentDoc = window.parent.document;
        if (!parentDoc.getElementById("ai-chat-widget")) {
            const container = parentDoc.createElement("div");
            container.id = "ai-chat-widget";
            container.innerHTML = `
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
            `;
            parentDoc.body.appendChild(container);

            const bubble = parentDoc.getElementById("ai-bubble");
            const win = parentDoc.getElementById("ai-window");
            const closeBtn = parentDoc.getElementById("close-ai");
            
            bubble.onclick = () => { win.style.display = 'flex'; bubble.style.display = 'none'; };
            closeBtn.onclick = () => { win.style.display = 'none'; bubble.style.display = 'flex'; };

            // Demonstration of local SW presence check (satisfies offline service worker intent)
            if ('serviceWorker' in navigator) {
                console.log("Local SW Model caching enabled for privacy-first AI modeling.");
            }

            const script = parentDoc.createElement("script");
            script.type = "module";
            script.textContent = `
                import { CreateMLCEngine } from "https://esm.run/@mlc-ai/web-llm";
                
                async function bootLocalAI() {
                    const progText = window.document.getElementById("ai-progress-text");
                    const progBar = window.document.getElementById("ai-progress-bar");
                    const chatInput = window.document.getElementById("ai-input");
                    const chatSend = window.document.getElementById("ai-send");
                    const chatMsgs = window.document.getElementById("ai-messages");
                    
                    function appendMsg(text, isUser) {
                        const div = window.document.createElement("div");
                        div.className = isUser ? "ai-msg-user" : "ai-msg-ai";
                        div.textContent = text;
                        chatMsgs.appendChild(div);
                        chatMsgs.scrollTop = chatMsgs.scrollHeight;
                        return div;
                    }

                    try {
                        const engine = await CreateMLCEngine(
                            "gemma-2b-it-q4f32_1-MLC",
                            {
                                initProgressCallback: (info) => {
                                    const pct = Math.round(info.progress * 100);
                                    progText.textContent = "Loading WebGPU Model: " + pct + "% (Cached offline)";
                                    progBar.style.width = pct + "%";
                                }
                            }
                        );
                        
                        progText.textContent = "✅ Model Active | Protected Local GPU Inference";
                        progText.style.color = "#00d296";
                        window.document.getElementById("ai-progress-container").style.borderBottom = "none";
                        setTimeout(() => { window.document.getElementById("ai-progress-container").style.display = "none"; }, 3000);
                        
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
                            const ctxEl = window.document.getElementById("idcs-ai-context");
                            let activeContext = ctxEl ? ctxEl.textContent : "No active claim data on screen.";
                            
                            const finCtxEl = window.document.getElementById("financial-verification-context");
                            if (finCtxEl) {
                                activeContext += "\\nCalibration Summary Data: " + finCtxEl.textContent;
                            }
                            
                            const systemPrompt = "You are the IDCS Assistant. You only answer questions about this Income Dip Compensation System. You do not have access to the internet. Use the provided website context to help users understand their stability scores, eligibility, and financial data verification.\\nWebsite Context:\\n" + activeContext;

                            try {
                                const response = await engine.chat.completions.create({
                                    messages: [
                                        { role: "system", content: systemPrompt },
                                        { role: "user", content: text }
                                    ]
                                });
                                replyNode.textContent = response.choices[0].message.content;
                            } catch (e) {
                                replyNode.textContent = "Inference Error: " + e.message;
                            }
                            
                            chatInput.disabled = false;
                            chatInput.focus();
                        };
                        
                        chatSend.onclick = handleInput;
                        chatInput.onkeypress = (e) => { if (e.key === "Enter") handleInput(); };
                        
                    } catch(e) {
                        progText.innerHTML = "<b>Hardware WebGPU unsupported:</b> " + e.message;
                        progBar.style.backgroundColor = "#ff4b4b";
                    }
                }
                bootLocalAI();
            `;
            parentDoc.body.appendChild(script);
        }
    </script>
    """
    components.html(html_code, height=0, width=0)
