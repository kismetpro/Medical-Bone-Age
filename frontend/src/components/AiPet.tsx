import { useState, useRef, useEffect } from 'react';

const AiPet = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([{ role: 'ai', content: '你好！我是骨龄预测小精灵，有什么可以帮您？' }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      // 注意：生产环境建议通过后端转发，此处为直接调用示例
      const response = await fetch('https://api.deepseek.com/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer YOUR_DEEPSEEK_API_KEY` // 替换为你的Key
        },
        body: JSON.stringify({
          model: "deepseek-chat",
          messages: [
            { role: "system", content: "你是一个专业的医疗AI小助手，专注于骨龄预测和儿童健康咨询。" },
            ...messages.map(m => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.content })),
            { role: "user", content: input }
          ],
          stream: false
        })
      });

      const data = await response.json();
      const aiReply = data.choices[0].message.content;
      setMessages(prev => [...prev, { role: 'ai', content: aiReply }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'ai', content: '抱歉，我连接不到大脑了...' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-pet-fixed-container">
      {/* 聊天窗口 */}
      {isOpen && (
        <div className="chat-box">
          <div className="chat-header">
            AI 问诊小精灵
            <button onClick={() => setIsOpen(false)}>×</button>
          </div>
          <div className="chat-content" ref={scrollRef}>
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
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="问问骨龄知识..."
            />
            <button onClick={handleSend} disabled={loading}>发送</button>
          </div>
        </div>
      )}

      {/* 小精灵形象（点击开关） */}
      <div className={`pet-avatar ${isOpen ? 'active' : ''}`} onClick={() => setIsOpen(!isOpen)}>
        <img src="/path-to-your-sprite.png" alt="AI精灵" />
      </div>
    </div>
  );
};

export default AiPet;
