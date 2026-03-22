import { useState, useRef, useEffect } from 'react';
import { X, Image as ImageIcon, User } from 'lucide-react';
import AI_LOGO from '../static/AI_logo.jpg';

interface Message {
  role: 'user' | 'ai';
  content: string;
  image?: string;
  timestamp?: string;
}

const AiPet = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([{ 
    role: 'ai', 
    content: '👋 你好！我是骨龄预测AI小助手，专注于儿童骨骼发育和健康咨询。有什么可以帮您吗？',
    timestamp: new Date().toLocaleTimeString()
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [showImageModal, setShowImageModal] = useState(false);
  const [modalImage, setModalImage] = useState<string>('');
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setPreviewImage(ev.target?.result as string);
        setSelectedImage(ev.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeSelectedImage = () => {
    setSelectedImage(null);
    setPreviewImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const showImagePreview = (imageUrl: string) => {
    setModalImage(imageUrl);
    setShowImageModal(true);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    e.preventDefault();
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleSend = async () => {
    if ((!input.trim() && !selectedImage) || loading) return;

    const userMsg: Message = {
      role: 'user',
      content: input,
      image: selectedImage || undefined,
      timestamp: new Date().toLocaleTimeString()
    };
    
    const currentInput = input;
    const currentImage = selectedImage;
    
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setSelectedImage(null);
    setPreviewImage(null);
    setLoading(true);

    const aiMsgIndex = messages.length + 1;
    setMessages(prev => [...prev, { 
      role: 'ai', 
      content: '',
      timestamp: new Date().toLocaleTimeString()
    }]);

    try {
      const response = await fetch('https://api.deepseek.com/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer sk-c0b9488d8daf48099f9ee40edd21f541`
        },
        body: JSON.stringify({
          model: "deepseek-chat",
          messages: [
            { role: "system", content: "你是一个专业的医疗AI助手，专注于骨龄预测、儿童生长发育和健康咨询。回答要专业、准确、友好。如果用户发送了图片，请基于图片内容进行分析。" },
            ...messages.map(m => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.content })),
            { 
              role: "user", 
              content: currentImage 
                ? `[用户发送了一张图片]\n${currentInput || '请分析这张图片'}` 
                : currentInput 
            }
          ],
          stream: true
        })
      });

      if (!response.ok) throw new Error('API_ERROR');
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') continue;

              try {
                const json = JSON.parse(data);
                const content = json.choices?.[0]?.delta?.content;
                if (content) {
                  fullContent += content;
                  setMessages(prev => {
                    const newMessages = [...prev];
                    if (newMessages[aiMsgIndex]) {
                      newMessages[aiMsgIndex].content = fullContent;
                    }
                    return newMessages;
                  });
                }
              } catch (e) {
                console.error('解析流数据失败:', e);
              }
            }
          }
        }
      }

      if (!fullContent) {
        setMessages(prev => {
          const newMessages = [...prev];
          if (newMessages[aiMsgIndex]) {
            newMessages[aiMsgIndex].content = '抱歉，我暂时无法回应，请稍后再试。';
          }
          return newMessages;
        });
      }
    } catch (error) {
      console.error("AI助手出错:", error);
      setMessages(prev => {
        const newMessages = [...prev];
        if (newMessages[aiMsgIndex]) {
          newMessages[aiMsgIndex].content = '😔 抱歉，我连接不到大脑了...请检查网络连接或API配置。';
        }
        return newMessages;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      {showImageModal && (
        <div className="image-preview-modal" onClick={() => setShowImageModal(false)}>
          <img src={modalImage} alt="预览" onClick={(e) => e.stopPropagation()} />
          <button className="close-btn" onClick={() => setShowImageModal(false)}>
            <X size={24} />
          </button>
        </div>
      )}

      {isOpen && (
        <div 
          className="chat"
          style={{
            transform: `translate(${position.x}px, ${position.y}px)`,
            cursor: isDragging ? 'grabbing' : 'default'
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <div className="chat-title">
            <div className="avatar">
              <img src={AI_LOGO} alt="AI" />
            </div>
            <div>
              <h1>AI 骨龄助手</h1>
              <h2>在线</h2>
            </div>
            <button className="chat-close-btn" onClick={() => setIsOpen(false)}>
              <X size={18} />
            </button>
          </div>
          
          <div className="messages">
            <div className="messages-content" ref={scrollRef}>
              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role === 'user' ? 'message-personal' : ''} new`}>
                  <div className="avatar">
                    {msg.role === 'ai' ? (
                      <img src={AI_LOGO} alt="AI" />
                    ) : (
                      <User size={16} color="white" />
                    )}
                  </div>
                  {msg.content && <div>{msg.content}</div>}
                  {msg.image && (
                    <img 
                      src={msg.image} 
                      alt="用户上传的图片" 
                      onClick={() => showImagePreview(msg.image!)}
                    />
                  )}
                  {msg.timestamp && <div className="timestamp">{msg.timestamp}</div>}
                </div>
              ))}
              {loading && messages[messages.length - 1]?.content === '' && (
                <div className="message loading">
                  <div className="avatar">
                    <img src={AI_LOGO} alt="AI" />
                  </div>
                  <span></span>
                </div>
              )}
            </div>
          </div>
          
          <div className="message-box">
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept="image/*"
              onChange={handleImageSelect}
            />
            <button 
              className="image-upload-btn"
              onClick={() => fileInputRef.current?.click()}
              title="上传图片"
            >
              <ImageIcon size={20} />
            </button>
            
            <input 
              className="message-input"
              value={input} 
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="输入您的问题..."
              disabled={loading}
            />
            
            <button 
              className="message-submit" 
              onClick={handleSend} 
              disabled={loading || (!input.trim() && !selectedImage)}
            >
              发送
            </button>
          </div>

          {previewImage && (
            <div style={{
              position: 'absolute',
              bottom: '60px',
              left: '12px',
              right: '12px',
              background: 'rgba(0, 0, 0, 0.8)',
              borderRadius: '10px',
              padding: '10px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              animation: 'fadeIn 0.2s ease'
            }}>
              <img 
                src={previewImage} 
                alt="预览" 
                style={{ 
                  width: '60px', 
                  height: '60px', 
                  borderRadius: '8px',
                  objectFit: 'cover'
                }}
              />
              <div style={{ flex: 1, fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>
                已选择图片
              </div>
              <button 
                onClick={removeSelectedImage}
                style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: 'none',
                  color: 'white',
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <X size={16} />
              </button>
            </div>
          )}
        </div>
      )}

      <div 
        className="pet-avatar" 
        onClick={() => setIsOpen(!isOpen)}
      >
        <img src={AI_LOGO} alt="AI" />
      </div>
    </div>
  );
};

export default AiPet;
