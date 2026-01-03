import React, { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, Loader2, Sparkles, Plus, MessageSquare, Trash2, LogOut, Code, List, Slack, Mail, ChevronRight, Menu, Github, Cloud, Database, Terminal, Search, FileText, Calendar, Globe } from 'lucide-react'
import Auth from './Auth'
import './App.css'

function App() {
    const [userId, setUserId] = useState(localStorage.getItem('userId'))
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [chats, setChats] = useState([])
    const [activeChatId, setActiveChatId] = useState(null)
    const [sidebarOpen, setSidebarOpen] = useState(true)

    // Slash Command State
    const [slashMenu, setSlashMenu] = useState({ open: false, type: 'services', data: [], selectedIndex: 0, triggerIndex: 0 });
    const [activeService, setActiveService] = useState(null)

    // Account Selection State
    const [accountSelection, setAccountSelection] = useState({ open: false, service: null, accounts: [], pendingQuery: null })
    const [selectedAccounts, setSelectedAccounts] = useState({})

    // Context Selection State (for pages, repos, etc.)
    const [contextSelection, setContextSelection] = useState({ open: false, service: null, type: null, options: [], pendingQuery: null, search: '' })
    const [selectedContext, setSelectedContext] = useState({})
    const [braveModalOpen, setBraveModalOpen] = useState(false);
    const [braveKey, setBraveKey] = useState('');

    // For Rich Input Cursor Stability
    const composerRef = useRef(null);
    const lastValueRef = useRef('');

    const messagesEndRef = useRef(null)

    const serviceData = [
        { id: 'github', name: 'GitHub', icon: <Github size={16} />, color: '#60a5fa' },
        { id: 'notion', name: 'Notion', icon: <FileText size={16} />, color: '#34d399' },
        { id: 'slack', name: 'Slack', icon: <Slack size={16} />, color: '#a78bfa' },
        { id: 'gmail', name: 'Gmail', icon: <Mail size={16} />, color: '#f472b6' },
        { id: 'calendar', name: 'Calendar', icon: <Calendar size={16} />, color: '#fbbf24' },
        { id: 'web-search', name: 'Search', icon: <Globe size={16} />, color: '#ff4f00' },
        { id: 'salesforce', name: 'Salesforce', icon: <Cloud size={16} />, color: '#6366f1' },
    ];

    const servicePrompts = {
        github: [
            "Create a private repository named 'Project-X'",
            "List my recent pull requests",
            "Check issues assigned to me",
            "Get repository details for 'Connective'"
        ],
        notion: [
            "List my recently edited pages",
            "Search for 'Meeting Notes'",
            "Summarize my recent research notes",
            "Check my task database updates"
        ],
        slack: [
            "Send 'Finished the task' to #general",
            "List active channels in my team",
            "Who is currently online?",
            "Check recent mentions in Slack"
        ],
        gmail: [
            "Search my inbox for 'Subscription'",
            "List my recent emails",
            "Send an email to manager@company.com",
            "Are there any unread messages?"
        ],
        salesforce: [
            "Show my open lead opportunities",
            "List my high-priority accounts",
            "Get contact info for 'John Smith'",
            "List recent sales activities"
        ],
        calendar: [
            "What's on my schedule today?",
            "List my upcoming meetings",
            "Schedule a call tomorrow at 10am",
            "Add 'Review Session' to my calendar"
        ],
        "web-search": [
            "Search for latest AI news",
            "What's the weather in Tokyo?",
            "DuckDuckGo search for 'MCP'",
            "Find top news stories today"
        ]
    };

    const suggestions = [
        { icon: <Code size={18} />, text: "Create a private Repo named 'Project-X'", color: "#60a5fa" },
        { icon: <List size={18} />, text: "List my recent Notion pages", color: "#34d399" },
        { icon: <Slack size={18} />, text: "Message #general in Slack", color: "#a78bfa" },
        { icon: <Mail size={18} />, text: "Unread emails in Gmail", color: "#f472b6" },
    ]

    const handleSuggestion = (text) => setInput(text);
    const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const authSuccess = params.get('auth_success');
        const returnedUserId = params.get('userId');
        const token = params.get('token');

        if (authSuccess) {
            if (returnedUserId) {
                localStorage.setItem('userId', returnedUserId);
                setUserId(returnedUserId);
            }
            if (token) {
                localStorage.setItem('token', token);
            }
            window.history.replaceState({}, '', window.location.pathname);
            checkStatus();

            const pending = localStorage.getItem('pending_action');
            const pendingChatId = localStorage.getItem('pending_chat_id');

            if (pending) {
                localStorage.removeItem('pending_action');
                localStorage.removeItem('pending_chat_id');
                if (pendingChatId) {
                    setActiveChatId(pendingChatId);
                    loadChat(pendingChatId);
                }
                setTimeout(() => processQuery(pending, true, pendingChatId), 1000);
            }
        } else if (userId) {
            checkStatus();
        }
    }, [userId]);

    const checkStatus = async () => {
        if (!userId) return;
        const token = localStorage.getItem('token');
        try {
            const res = await fetch(`http://localhost:3000/api/status`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.status === 401) { handleLogout(); return; }
            const data = await res.json();
            setChats(data.chats || []);

            // Removed auto-load logic to prevent new chat race conditions

        } catch (e) {
            console.error("Failed to check status", e);
        }
    }

    const loadChat = async (chatId) => {
        setActiveChatId(chatId);
        setLoading(true);
        const token = localStorage.getItem('token');
        try {
            const res = await fetch(`http://localhost:3000/api/chats/${chatId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            setMessages(data.messages || []);
            setSelectedAccounts({});
            setSelectedContext({});
        } catch (e) {
            console.error("Failed to load chat", e);
        } finally {
            setLoading(false);
        }
    }

    const startNewChat = async () => {
        setMessages([]);
        setActiveChatId(null);
        setSelectedAccounts({});
        setSelectedContext({});
    }

    const deleteChat = async (e, chatId) => {
        e.stopPropagation();
        const token = localStorage.getItem('token');
        try {
            await fetch(`http://localhost:3000/api/chats/${chatId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            setChats(prev => prev.filter(c => c.id !== chatId));
            if (activeChatId === chatId) {
                startNewChat();
            }
        } catch (e) {
            console.error("Failed to delete chat", e);
        }
    }

    // Input Change Handler for Rich Composer
    const handleInputChange = (e) => {
        const value = e.target.innerText;
        lastValueRef.current = value;
        setInput(value);

        // Get cursor position in contenteditable
        const selection = window.getSelection();
        if (!selection.rangeCount) return;
        const range = selection.getRangeAt(0);
        const cursorPos = range.startOffset;

        // Find the word being typed (at cursor)
        const textBeforeCursor = value.substring(0, cursorPos);
        const lastSlashIndex = textBeforeCursor.lastIndexOf('/');

        if (lastSlashIndex !== -1) {
            const isAtStart = lastSlashIndex === 0;
            const isAfterSpace = textBeforeCursor[lastSlashIndex - 1] === ' ';

            if (isAtStart || isAfterSpace) {
                const commandText = textBeforeCursor.substring(lastSlashIndex + 1).toLowerCase();
                const filtered = serviceData.filter(s => s.id.startsWith(commandText));

                if (filtered.length > 0) {
                    setSlashMenu({
                        open: true,
                        type: 'services',
                        data: filtered,
                        selectedIndex: 0,
                        triggerIndex: lastSlashIndex
                    });
                    return;
                }
            }
        }

        setSlashMenu(prev => ({ ...prev, open: false }));
    };

    // Effect to sync rich input with state changes from OUTSIDE (e.g. menu selection)
    useEffect(() => {
        if (composerRef.current && input !== lastValueRef.current) {
            composerRef.current.innerHTML = renderMessageHTML(input);
            lastValueRef.current = input;

            // Move cursor to end after external update
            const range = document.createRange();
            const sel = window.getSelection();
            range.selectNodeContents(composerRef.current);
            range.collapse(false);
            sel.removeAllRanges();
            sel.addRange(range);
        }
    }, [input]);

    const handleSelectPrompt = (prompt) => {
        setInput(prompt);
        setSlashMenu({ open: false, type: 'services', data: [], selectedIndex: 0 });
        // Optionally auto-submit: 
        const finalQuery = activeService ? `/${activeService.id} ${prompt}` : prompt;
        processQuery(finalQuery);
    };

    const handleSelectService = (service) => {
        const triggerIndex = slashMenu.triggerIndex || 0;
        const textBefore = input.substring(0, triggerIndex);
        const textToEnd = input.substring(triggerIndex);
        const firstSpaceAfterSlash = textToEnd.indexOf(' ');
        const textAfter = firstSpaceAfterSlash !== -1 ? textToEnd.substring(firstSpaceAfterSlash) : '';

        const newValue = textBefore + `/${service.id}` + textAfter;
        setInput(newValue);
        setSlashMenu({ open: false, type: 'services', data: [], selectedIndex: 0 });
    };

    const removeService = () => {
        setActiveService(null);
        setSlashMenu({ open: false, type: 'services', data: [], selectedIndex: 0 });
    };

    const handleSubmit = async (e) => {
        if (e) e.preventDefault();
        if ((!input.trim() && !activeService) || loading) return;
        setSlashMenu({ open: false, data: [] });

        const finalQuery = activeService ? `/${activeService.id} ${input}` : input;
        await processQuery(finalQuery);
    };

    const processQuery = async (queryText, isRetry = false, forcedChatId = null, forcedAccounts = null, forcedContext = null) => {
        let currentAccounts = forcedAccounts || { ...selectedAccounts };
        let currentContext = forcedContext || { ...selectedContext };

        if (!isRetry) {
            const userMessage = { role: 'user', text: queryText }
            setMessages(prev => [...prev, userMessage]);
        }

        setInput('')
        setLoading(true)

        const token = localStorage.getItem('token');
        try {
            const response = await fetch(`http://localhost:3000/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    message: queryText,
                    history: messages.map(m => ({
                        role: m.role === 'user' ? 'user' : 'model',
                        parts: [{ text: m.text }]
                    })),
                    chatId: forcedChatId || activeChatId,
                    isRetry: isRetry,
                    selectedAccounts: currentAccounts,
                    selectedContext: currentContext
                })
            })

            if (response.status === 401) { handleLogout(); return; }

            const data = await response.json()

            if (data.chatId && !activeChatId) {
                setActiveChatId(data.chatId);
                // Don't call checkStatus here to avoid state race conditions
            }

            // Handle Account Selection Request
            if (data.action === "select_account") {
                setAccountSelection({
                    open: true,
                    service: data.service,
                    accounts: data.accounts,
                    pendingQuery: queryText
                });
                setLoading(false);
                return;
            }

            // Handle Context Selection Request (e.g. Pages, Repos)
            if (data.action === "select_context") {
                setContextSelection({
                    open: true,
                    service: data.service,
                    type: data.context_type,
                    options: data.options,
                    pendingQuery: queryText
                });
                setLoading(false);
                return;
            }

            if (data.redirect) {
                localStorage.setItem('pending_action', queryText);
                if (data.chatId) {
                    localStorage.setItem('pending_chat_id', data.chatId);
                }
                setMessages(prev => [...prev, { role: 'model', text: data.response || "I'm redirecting you to authentication..." }]);
                setTimeout(() => window.location.href = data.redirect, 1500);
                return;
            }

            if (data.error) throw new Error(data.error)

            if (data.chatId && !activeChatId) {
                setActiveChatId(data.chatId);
            }


            setMessages(prev => [...prev, { role: 'model', text: data.response }])
        } catch (error) {
            setMessages(prev => [...prev, { role: 'model', text: 'Error: ' + error.message }])
        } finally {
            setLoading(false)
        }
    }

    const selectAccount = async (accountId) => {
        const service = accountSelection.service;
        const newSelection = { ...selectedAccounts, [service]: accountId };
        setSelectedAccounts(newSelection);
        setAccountSelection({ open: false, service: null, accounts: [], pendingQuery: null });
        const currentChatId = activeChatId;
        await processQuery(accountSelection.pendingQuery, true, currentChatId, newSelection, selectedContext);

    }

    const selectContext = async (optionId) => {
        const service = contextSelection.service;
        const type = contextSelection.type;
        const key = `${service}_${type}`;
        const newContext = { ...selectedContext, [key]: optionId };
        setSelectedContext(newContext);
        setContextSelection({ open: false, service: null, type: null, options: [], pendingQuery: null });
        const currentChatId = activeChatId;
        await processQuery(contextSelection.pendingQuery, true, currentChatId, selectedAccounts, newContext);

    }

    const connectNewAccount = (service) => {
        setAccountSelection({ open: false, service: null, accounts: [], pendingQuery: null });
        window.location.href = `http://localhost:3000/api/auth/${service}/login?userId=${userId}`;
    }


    const handleLogout = () => {
        localStorage.clear();
        setUserId(null);
        setMessages([]);
    }

    const getServiceIcon = (id) => {
        switch (id) {
            case 'github': return <Github size={16} />;
            case 'notion': return <FileText size={16} />;
            case 'slack': return <Slack size={16} />;
            case 'gmail': return <Mail size={16} />;
            case 'calendar': return <Calendar size={16} />;
            case 'web-search': return <Globe size={16} />;
            case 'salesforce': return <Cloud size={16} />;
            default: return <Terminal size={16} />;
        }
    }

    const renderMessageHTML = (text) => {
        if (!text) return '';
        const parts = text.split(/(\/\w+)/g);
        return parts.map(part => {
            if (part.startsWith('/')) {
                const serviceId = part.substring(1).toLowerCase();
                const matchedId = serviceId;
                const service = serviceData.find(s => s.id === matchedId);
                if (service) {
                    const iconSvg = serviceId === 'github' ? '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path>' :
                        serviceId === 'notion' ? '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline>' :
                            serviceId === 'slack' ? '<path d="M14.5 10c-.83 0-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5z"></path><path d="M20.5 10c-.83 0-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5z"></path><path d="M9.5 14c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5s-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5z"></path><path d="M3.5 14c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5s-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5z"></path>' :
                                serviceId === 'gmail' ? '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline>' :
                                    serviceId === 'calendar' ? '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line>' :
                                        serviceId === 'web-search' ? '<circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>' :
                                            serviceId === 'salesforce' ? '<path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path>' :
                                                '<circle cx="12" cy="12" r="3"></circle><path d="M3 12h3"></path><path d="M18 12h3"></path><path d="M12 3v3"></path><path d="M12 18v3"></path><path d="M5.6 5.6l2.1 2.1"></path><path d="M16.3 16.3l2.1 2.1"></path><path d="M5.6 16.3l2.1-2.1"></path><path d="M16.3 5.6l2.1-2.1"></path>';

                    return `<span class="inline-service-tag" contenteditable="false" style="color: ${service.color}; background-color: ${service.color}15; border-color: ${service.color}30">` +
                        `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${iconSvg}</svg>` +
                        `<span>${service.name}</span></span>`;
                }
            }
            return part;
        }).join('');
    };

    const renderMessageText = (text) => {
        if (!text) return '';
        const parts = text.split(/(\/\w+)/g);
        return parts.map((part, i) => {
            if (part.startsWith('/')) {
                const serviceId = part.substring(1).toLowerCase();
                const service = serviceData.find(s => s.id === serviceId);
                if (service) {
                    return (
                        <span key={i} className="inline-service-tag" style={{ color: service.color, backgroundColor: `${service.color}15`, borderColor: `${service.color}30` }}>
                            {service.icon}
                            <span>{service.name}</span>
                        </span>
                    );
                }
            }
            return part;
        });
    };

    if (!userId) {
        return <Auth onLogin={setUserId} />;
    }

    return (
        <div className="dashboard-container">
            <aside className={`sidebar glass ${sidebarOpen ? 'open' : 'closed'}`}>
                <div className="sidebar-header">
                    <button className="new-chat-btn" onClick={startNewChat}>
                        <Plus size={20} />
                        <span>New Chat</span>
                    </button>
                </div>

                <div className="chat-explorer">
                    <p className="section-title">Recent Chats</p>
                    <div className="chat-list">
                        {chats.map(chat => (
                            <div
                                key={chat.id}
                                className={`chat-item ${activeChatId === chat.id ? 'active' : ''}`}
                                onClick={() => loadChat(chat.id)}
                            >
                                <MessageSquare size={16} />
                                <span className="chat-title">
                                    {chat.title && chat.title.startsWith('/') ? chat.title.split(' ').slice(1).join(' ') : chat.title}
                                </span>
                                <button className="delete-chat" onClick={(e) => deleteChat(e, chat.id)}>
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="sidebar-footer">
                    <div className="user-info">
                        <div className="user-avatar">
                            {userId.charAt(0).toUpperCase()}
                        </div>
                        <div className="user-details">
                            <span className="username">{userId}</span>
                            <span className="user-status">Online</span>
                        </div>
                    </div>
                    <button className="icon-btn logout" onClick={handleLogout} title="Logout">
                        <LogOut size={20} />
                    </button>
                </div>
            </aside>

            <main className="main-content">
                <header className="top-nav glass">
                    <div className="nav-left">
                        <button className="icon-btn menu-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
                            <Menu size={20} />
                        </button>
                        <div className="logo-section">
                            <Sparkles className="logo-icon" />
                            <h1>Connective</h1>
                        </div>
                    </div>
                </header>

                <div className="chat-viewport">
                    {messages.length === 0 ? (
                        <div className="empty-state">
                            <div className="bot-hero">
                                <div className="bot-orb">
                                    <Bot size={40} />
                                </div>
                                <h2>Welcome back, {userId}</h2>
                                <p>How can I assist your workflow today?</p>
                            </div>

                            <div className="suggestions-grid">
                                {suggestions.map((s, i) => (
                                    <button key={i} className="suggestion-tile glass" onClick={() => handleSuggestion(s.text)}>
                                        <div className="tile-icon" style={{ backgroundColor: `${s.color}20`, color: s.color }}>
                                            {s.icon}
                                        </div>
                                        <div className="tile-content">
                                            <span>{s.text}</span>
                                            <ChevronRight size={14} />
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="messages-flow">
                            {messages.map((m, i) => (
                                <div key={i} className={`message-row ${m.role}`}>
                                    <div className="message-content">
                                        <div className="avatar">
                                            {m.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                                        </div>
                                        <div className="bubble glass">
                                            <div className="bubble-text">
                                                {renderMessageText(m.text)}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {loading && (
                                <div className="message-row model">
                                    <div className="message-content">
                                        <div className="avatar">
                                            <Bot size={18} />
                                        </div>
                                        <div className="bubble loading glass">
                                            <Loader2 size={18} className="animate-spin" />
                                        </div>
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                <footer className="composer-area">
                    {/* Slash Command Menu */}
                    {slashMenu.open && (
                        <div className="slash-menu-container glass">
                            <div className="slash-menu-header">
                                <span>Connective Services</span>
                            </div>
                            <div className="slash-menu-list">
                                {slashMenu.data.map((item, index) => (
                                    <button
                                        key={slashMenu.type === 'services' ? item.id : index}
                                        className={`slash-menu-item ${slashMenu.selectedIndex === index ? 'selected' : ''}`}
                                        onClick={() => {
                                            if (slashMenu.type === 'services') handleSelectService(item);
                                            else handleSelectPrompt(item);
                                        }}
                                    >
                                        {slashMenu.type === 'services' ? (
                                            <>
                                                <span className="item-icon" style={{ color: item.color }}>{item.icon}</span>
                                                <span className="item-name">{item.name}</span>
                                                <span className="item-hint">/ {item.id}</span>
                                            </>
                                        ) : null}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    <form className="input-box glass" onSubmit={handleSubmit}>
                        <div
                            ref={composerRef}
                            className="rich-input"
                            contentEditable={!loading}
                            onInput={handleInputChange}
                            onFocus={() => { if (input.includes('/')) setSlashMenu({ ...slashMenu, open: true, selectedIndex: 0 }) }}
                            onKeyDown={(e) => {
                                if (slashMenu.open && (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter')) {
                                    e.preventDefault();
                                    if (e.key === 'ArrowDown') {
                                        setSlashMenu(prev => ({ ...prev, selectedIndex: (prev.selectedIndex + 1) % prev.data.length }));
                                    } else if (e.key === 'ArrowUp') {
                                        setSlashMenu(prev => ({ ...prev, selectedIndex: (prev.selectedIndex - 1 + prev.data.length) % prev.data.length }));
                                    } else if (e.key === 'Enter' && slashMenu.data[slashMenu.selectedIndex]) {
                                        handleSelectService(slashMenu.data[slashMenu.selectedIndex]);
                                    }
                                    return;
                                }
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSubmit();
                                }
                            }}
                        ></div>
                        <button type="submit" className="action-btn send" disabled={(!input.trim()) || loading}>
                            <Send size={18} />
                        </button>
                    </form>
                    <p className="disclaimer">Powered by Connective AI Core</p>
                </footer>
            </main>

            {/* Account Selection Modal */}
            {accountSelection.open && (
                <div className="modal-overlay" onClick={() => setAccountSelection({ ...accountSelection, open: false })}>
                    <div className="modal-content glass" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-inner">
                            <div className="modal-header">
                                <h3 className="modal-title">Select Account</h3>
                                <button className="modal-close" onClick={() => setAccountSelection({ ...accountSelection, open: false })}>
                                    <Plus size={20} style={{ transform: 'rotate(45deg)' }} />
                                </button>
                            </div>
                            <p className="modal-subtitle">Multiple {accountSelection.service} accounts found. Which one should I use?</p>

                            <div className="account-options">
                                {accountSelection.accounts.map(acc => (
                                    <button key={acc.id} className="account-option-btn" onClick={() => selectAccount(acc.id)}>
                                        <div className="account-icon-wrapper">
                                            {getServiceIcon(accountSelection.service)}
                                        </div>
                                        <div className="account-info">
                                            <span className="account-label">{acc.label}</span>
                                            <span className="account-id">ID: {acc.id}</span>
                                        </div>
                                    </button>
                                ))}

                                <button className="account-option-btn new-account" onClick={() => connectNewAccount(accountSelection.service)}>
                                    <Plus size={18} />
                                    <span>Connect New Account</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Context Selection Modal (e.g. Pages, Repos) */}
            {contextSelection.open && (
                <div className="modal-overlay" onClick={() => setContextSelection({ ...contextSelection, open: false })}>
                    <div className="modal-content glass" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-inner">
                            <div className="modal-header">
                                <h3 className="modal-title">Select {contextSelection.service === 'notion' ? 'Notion Resource' : 'Resource'}</h3>
                                <button className="modal-close" onClick={() => setContextSelection({ ...contextSelection, open: false })}>
                                    <Plus size={20} style={{ transform: 'rotate(45deg)' }} />
                                </button>
                            </div>
                            <p className="modal-subtitle">Pick the {contextSelection.type} you'd like me to interact with.</p>

                            <div className="search-filter-wrapper glass">
                                <Search size={16} />
                                <input
                                    type="text"
                                    placeholder={`Search ${contextSelection.type}s...`}
                                    value={contextSelection.search || ''}
                                    onChange={(e) => setContextSelection({ ...contextSelection, search: e.target.value })}
                                />
                            </div>

                            <div className="account-options" style={{ marginTop: '20px' }}>
                                {contextSelection.options
                                    .filter(opt => opt.label.toLowerCase().includes((contextSelection.search || '').toLowerCase()))
                                    .map(opt => (
                                        <button key={opt.id} className="account-option-btn" onClick={() => selectContext(opt.id)}>
                                            <div className="account-icon-wrapper" style={{ backgroundColor: opt.type === 'database' ? 'rgba(167, 139, 250, 0.1)' : 'rgba(52, 211, 153, 0.1)', color: opt.type === 'database' ? '#a78bfa' : '#34d399' }}>
                                                {opt.type === 'database' ? <Database size={18} /> : <FileText size={18} />}
                                            </div>
                                            <div className="account-info">
                                                <span className="account-label">{opt.label}</span>
                                                <span className="account-id" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                    {opt.type === 'database' ? 'Database' : 'Page'}
                                                </span>
                                            </div>
                                            <ChevronRight size={16} style={{ marginLeft: 'auto', opacity: 0.3 }} />
                                        </button>
                                    ))}
                                {contextSelection.options.filter(opt => opt.label.toLowerCase().includes((contextSelection.search || '').toLowerCase())).length === 0 && (
                                    <div className="no-results">No matches found for "{contextSelection.search}"</div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

// Added missing FileText import from lucide-react in the top import line above

export default App
