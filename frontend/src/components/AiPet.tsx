import { useState, useRef, useEffect, useCallback } from 'react';

const AiPet = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([{ role: 'ai', content: '你好！我是骨龄预测小精灵，有什么可以帮您？' }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 1. 安全滚动逻辑
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, loading]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = { role: 'user', content: input };
    const currentInput = input; // 闭包安全
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('https://api.deepseek.com/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer YOUR_API_KEY` // 建议从环境变量读取
        },
        body: JSON.stringify({
          model: "deepseek-chat",
          messages: [
            { role: "system", content: "你是一个专业的医疗AI小助手，专注于骨龄预测和儿童健康咨询。" },
            ...messages.map(m => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.content })),
            { role: "user", content: currentInput }
          ],
          stream: false
        })
      });

      // 2. 防御性数据解析
      if (!response.ok) throw new Error('API_ERROR');
      
      const data = await response.json();
      // 使用可选链 (?.) 防止崩溃
      const aiReply = data?.choices?.[0]?.message?.content || '我暂时无法回应，请稍后再试。';
      
      setMessages(prev => [...prev, { role: 'ai', content: aiReply }]);
    } catch (error) {
      console.error("AI精灵出错:", error);
      setMessages(prev => [...prev, { role: 'ai', content: '抱歉，我连接不到大脑了...请检查网络或API额度。' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    /* 核心修复：外层增加样式，防止遮挡侧边栏 */
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-end',
      pointerEvents: 'none' /* 容器不拦截点击 */
    }}>
      {/* 聊天窗口 */}
      {isOpen && (
        <div className="chat-box" style={{ 
          pointerEvents: 'auto', /* 窗口内部恢复点击 */
          marginBottom: '15px' 
        }}>
          <div className="chat-header">
            AI 问诊小精灵
            <button onClick={() => setIsOpen(false)}>×</button>
          </div>
          <div className="chat-content" ref={scrollRef} style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {messages.map((msg, i) => (
              <div key={i} className={`msg-bubble ${msg.role}`}>
                {msg.content}
              </div>
            ))}
            {loading && <div className="msg-bubble ai">正在思考...</div>}
          </div>
          <div className="chat-input">
            <input 
              value={input} 
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="问问骨龄知识..."
            />
            <button onClick={handleSend} disabled={loading}>发送</button>
          </div>
        </div>
      )}

      {/* 小精灵形象 */}
      <div 
        className={`pet-avatar ${isOpen ? 'active' : ''}`} 
        onClick={() => setIsOpen(!isOpen)}
        style={{ pointerEvents: 'auto', cursor: 'pointer' }}
      >
        <img src="/path-to-your-sprite.png" alt="AI精灵" style={{ width: '60px', height: '60px' }} />
      </div>
    </div>
  );
};

export default AiPet;