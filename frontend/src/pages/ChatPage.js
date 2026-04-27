import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import { ArrowLeft, Send, MessageSquare, User, Search } from 'lucide-react';

import { API, getApiError } from '../utils/api';

const ChatPage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [selectedContact, setSelectedContact] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    fetchUser();
    fetchContacts();
    fetchConversations();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  useEffect(() => {
    if (selectedContact) {
      fetchMessages(selectedContact.user_id);
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(() => fetchMessages(selectedContact.user_id), 5000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [selectedContact]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchUser = async () => {
    try {
      const res = await fetch(`${API}/auth/me`, { credentials: 'include' });
      if (!res.ok) { navigate('/login'); return; }
      setUser(await res.json());
    } catch { navigate('/login'); }
  };

  const fetchContacts = async () => {
    try {
      const res = await fetch(`${API}/chat/contacts`, { credentials: 'include' });
      if (res.ok) setContacts(await res.json());
    } catch {}
    setLoading(false);
  };

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API}/chat/conversations`, { credentials: 'include' });
      if (res.ok) setConversations(await res.json());
    } catch {}
  };

  const fetchMessages = async (partnerId) => {
    try {
      const res = await fetch(`${API}/chat/messages/${partnerId}`, { credentials: 'include' });
      if (res.ok) {
        setMessages(await res.json());
        fetchConversations();
      }
    } catch {}
  };

  const handleSend = async () => {
    if (!newMessage.trim() || !selectedContact) return;
    try {
      const res = await fetch(`${API}/chat/send`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ recipient_id: selectedContact.user_id, message: newMessage.trim() })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      setNewMessage('');
      fetchMessages(selectedContact.user_id);
    } catch (err) { toast.error(err.message); }
  };

  const getConvoForContact = (contactId) => conversations.find(c => c.partner_id === contactId);
  const roleColor = (role) => role === 'teacher' ? 'bg-amber-100 text-amber-700' : role === 'student' ? 'bg-sky-100 text-sky-700' : role === 'counsellor' ? 'bg-violet-100 text-violet-700' : 'bg-red-100 text-red-700';
  const roleCode = (contact) => contact.teacher_code || contact.student_code || '';

  const filteredContacts = contacts.filter(c =>
    (c.name || '').toLowerCase().includes(search.toLowerCase()) ||
    (c.email || '').toLowerCase().includes(search.toLowerCase()) ||
    (c.teacher_code || '').toLowerCase().includes(search.toLowerCase()) ||
    (c.student_code || '').toLowerCase().includes(search.toLowerCase())
  );

  const backRoute = user?.role === 'admin' ? '/admin-dashboard' : user?.role === 'counsellor' ? '/counsellor-dashboard' : user?.role === 'teacher' ? '/teacher-dashboard' : '/student-dashboard';

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200 px-4 py-3 flex items-center gap-3">
        <Button onClick={() => navigate(backRoute)} variant="outline" className="rounded-full" data-testid="chat-back-btn"><ArrowLeft className="w-4 h-4" /></Button>
        <MessageSquare className="w-6 h-6 text-sky-500" />
        <h1 className="text-lg font-bold text-slate-900">Messages</h1>
        {selectedContact && (
          <div className="ml-auto flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${roleColor(selectedContact.role)}`}>{selectedContact.role}</span>
            <span className="text-xs font-mono text-slate-500" data-testid="chat-partner-id">{roleCode(selectedContact)}</span>
            <span className="font-semibold text-slate-900 text-sm">{selectedContact.name}</span>
          </div>
        )}
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Contact List */}
        <div className="w-80 border-r border-slate-200 bg-white flex flex-col">
          <div className="p-3 border-b border-slate-100">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search contacts..." className="pl-9 rounded-full text-sm" data-testid="chat-search" />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {filteredContacts.length === 0 ? (
              <p className="text-center text-slate-400 text-sm p-8">No contacts available</p>
            ) : filteredContacts.map(contact => {
              const convo = getConvoForContact(contact.user_id);
              const isSelected = selectedContact?.user_id === contact.user_id;
              return (
                <div key={contact.user_id} onClick={() => setSelectedContact(contact)}
                  className={`p-3 border-b border-slate-50 cursor-pointer transition-colors ${isSelected ? 'bg-sky-50 border-l-4 border-l-sky-500' : 'hover:bg-slate-50'}`}
                  data-testid={`contact-${contact.user_id}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <p className="font-semibold text-slate-900 text-sm truncate">{contact.name}</p>
                        <span className={`px-1.5 py-0 rounded-full text-[9px] font-bold ${roleColor(contact.role)}`}>{contact.role?.charAt(0).toUpperCase()}</span>
                      </div>
                      <p className="text-[10px] text-slate-500 font-mono">{roleCode(contact) || contact.email}</p>
                      {convo && <p className="text-xs text-slate-400 truncate mt-0.5">{convo.last_message}</p>}
                    </div>
                    {convo?.unread_count > 0 && (
                      <span className="bg-sky-500 text-white text-[10px] w-5 h-5 rounded-full flex items-center justify-center font-bold flex-shrink-0">{convo.unread_count}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {!selectedContact ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageSquare className="w-16 h-16 text-slate-200 mx-auto mb-3" />
                <p className="text-slate-400 text-lg font-medium">Select a contact to start messaging</p>
              </div>
            </div>
          ) : (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="chat-messages-area">
                {messages.length === 0 ? (
                  <p className="text-center text-slate-400 text-sm py-12">No messages yet. Start the conversation!</p>
                ) : messages.map(msg => {
                  const isMine = msg.sender_id === user?.user_id;
                  return (
                    <div key={msg.message_id} className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[70%] rounded-2xl px-4 py-2.5 ${isMine ? 'bg-sky-500 text-white' : 'bg-white border border-slate-200 text-slate-900'}`}>
                        {!isMine && <p className="text-[10px] font-bold mb-0.5 opacity-70">{msg.sender_name} ({msg.sender_code})</p>}
                        <p className="text-sm">{msg.message}</p>
                        <p className={`text-[10px] mt-1 ${isMine ? 'text-sky-100' : 'text-slate-400'}`}>
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Message Input */}
              <div className="border-t border-slate-200 bg-white p-3 flex gap-2">
                <Input value={newMessage} onChange={e => setNewMessage(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleSend(); }}
                  placeholder="Type a message..." className="flex-1 rounded-full" data-testid="chat-input" />
                <Button onClick={handleSend} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full px-6" data-testid="chat-send-btn">
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
