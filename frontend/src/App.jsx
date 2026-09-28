import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [activeTab, setActiveTab] = useState('search');
  
  // Auth Form State
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('renter');

  // Search / NLP State
  const [searchQuery, setSearchQuery] = useState('');
  const [vehicles, setVehicles] = useState([]);
  const [nlpMatches, setNlpMatches] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState(null);

  // Booking Flow State
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [participants, setParticipants] = useState(1);
  const [selectedExtras, setSelectedExtras] = useState([]);
  const [bookingSuccess, setBookingSuccess] = useState(null);

  // Health Score & EV Guidance State
  const [healthScoreData, setHealthScoreData] = useState(null);
  const [evGuidanceData, setEvGuidanceData] = useState(null);
  const [tripDistance, setTripDistance] = useState(120);

  // Telematics State
  const [telematicsResult, setTelematicsResult] = useState(null);

  // Notifications State
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    fetchVehicles();
  }, []);

  const fetchVehicles = async () => {
    try {
      const res = await fetch(`${API_BASE}/vehicles`);
      const data = await res.json();
      setVehicles(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, role })
      });
      const data = await res.json();
      if (res.ok) {
        alert("Registration successful! Please login.");
      } else {
        alert(data.detail || "Registration failed");
      }
    } catch (err) {
      alert("Error registering user");
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.access_token);
        localStorage.setItem('token', data.access_token);
        setUser({ email, role });
        fetchNotifications(data.access_token);
        alert("Login successful!");
      } else {
        alert(data.detail || "Login failed");
      }
    } catch (err) {
      alert("Error logging in");
    }
  };

  const fetchNotifications = async (authToken) => {
    try {
      const res = await fetch(`${API_BASE}/gamification/notifications`, {
        headers: { 'Authorization': `Bearer ${authToken || token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleNlpSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery) return;
    try {
      const res = await fetch(`${API_BASE}/vehicles/search/match?q=${encodeURIComponent(searchQuery)}`);
      const data = await res.json();
      setNlpMatches(data.matches || []);
    } catch (err) {
      console.error(err);
    }
  };

  const inspectVehicle = async (v) => {
    setSelectedVehicle(v);
    setHealthScoreData(null);
    setEvGuidanceData(null);
    
    // Fetch Health Score
    try {
      const hsRes = await fetch(`${API_BASE}/vehicles/${v.id}/health-score`);
      if (hsRes.ok) setHealthScoreData(await hsRes.json());
    } catch (err) { console.error(err); }

    // Fetch EV Guidance if EV
    if (v.is_ev) {
      try {
        const evRes = await fetch(`${API_BASE}/vehicles/${v.id}/ev-guidance?trip_distance_miles=${tripDistance}`);
        if (evRes.ok) setEvGuidanceData(await evRes.json());
      } catch (err) { console.error(err); }
    }
  };

  const handleCreateBooking = async (e) => {
    e.preventDefault();
    if (!token) return alert("Please login first");
    try {
      const res = await fetch(`${API_BASE}/bookings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          vehicle_id: selectedVehicle.id,
          start_date: new Date(startDate).toISOString(),
          end_date: new Date(endDate).toISOString(),
          participants_count: Number(participants),
          bundled_extras: selectedExtras
        })
      });
      const data = await res.json();
      if (res.ok) {
        setBookingSuccess(data);
        fetchNotifications(token);
      } else {
        alert(data.detail || "Booking creation failed");
      }
    } catch (err) {
      alert("Error creating booking");
    }
  };

  const handleProcessPayment = async () => {
    if (!bookingSuccess) return;
    try {
      const res = await fetch(`${API_BASE}/payments/process-intent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          booking_id: bookingSuccess.id,
          amount: bookingSuccess.total_price,
          payment_method_id: 'pm_card_visa'
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert(`Payment of $${bookingSuccess.total_price} Succeeded! Receipt: ${data.receipt_url}`);
        fetchNotifications(token);
      }
    } catch (err) { alert("Payment failed"); }
  };

  const handleSimulateTelematics = async () => {
    if (!bookingSuccess) return alert("Create a booking first");
    try {
      const simulatedPoints = [
        { timestamp: "2026-09-28T10:00:00", speed_mph: 45.0, accel_g: -0.6, latitude: 37.7749, longitude: -122.4194 },
        { timestamp: "2026-09-28T10:00:05", speed_mph: 0.0, accel_g: -3.8, latitude: 37.7751, longitude: -122.4196 }
      ];
      const res = await fetch(`${API_BASE}/bookings/${bookingSuccess.id}/telematics`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(simulatedPoints)
      });
      if (res.ok) {
        const data = await res.json();
        setTelematicsResult(data);
      }
    } catch (err) { alert("Telematics simulation failed"); }
  };

  return (
    <div className="app-container">
      {/* Navbar */}
      <nav className="navbar">
        <div className="logo">⚡ RENTO <span>AI EV Fleet</span></div>
        <div className="nav-links">
          {user ? (
            <>
              <span style={{ fontSize: '0.9rem', color: '#a5b4fc' }}>👤 {user.email} ({user.role})</span>
              <button className="btn btn-secondary" onClick={() => { setUser(null); setToken(''); localStorage.removeItem('token'); }}>Logout</button>
            </>
          ) : (
            <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Not Logged In</span>
          )}
        </div>
      </nav>

      <main className="main-content">
        {/* Navigation Tabs */}
        <div className="tab-nav">
          <button className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`} onClick={() => setActiveTab('search')}>🔍 Vehicle Search & AI Match</button>
          <button className={`tab-btn ${activeTab === 'auth' ? 'active' : ''}`} onClick={() => setActiveTab('auth')}>🔑 Auth & Identity</button>
          <button className={`tab-btn ${activeTab === 'booking' ? 'active' : ''}`} onClick={() => setActiveTab('booking')}>🚗 Booking & Extras</button>
          <button className={`tab-btn ${activeTab === 'trip' ? 'active' : ''}`} onClick={() => setActiveTab('trip')}>⚡ Live Trip & Telematics</button>
        </div>

        {/* Tab 1: Search & NLP Car Match */}
        {activeTab === 'search' && (
          <div>
            <div className="search-bar-container">
              <h3>🤖 AI Natural-Language Vehicle Search</h3>
              <p style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Describe your trip naturally (e.g. "Cheap EV for weekend with child seat in San Francisco")</p>
              <form onSubmit={handleNlpSearch} className="search-input-group">
                <input 
                  type="text" 
                  style={{ flex: 1 }}
                  placeholder="Enter trip intent..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <button type="submit" className="btn btn-primary">Find AI Matches</button>
              </form>
            </div>

            {nlpMatches.length > 0 && (
              <div style={{ marginBottom: '2rem' }}>
                <h4>Top AI Match Rankings</h4>
                <div className="grid-cards">
                  {nlpMatches.map((m) => (
                    <div key={m.vehicle_id} className="card" style={{ border: '1px solid #6366f1' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3>{m.make} {m.model}</h3>
                        <span className="badge badge-status">Relevance: {m.relevance_score}%</span>
                      </div>
                      <div>
                        {m.matched_features.map((f, idx) => (
                          <span key={idx} className="badge badge-ev" style={{ marginRight: '0.4rem', marginBottom: '0.4rem', display: 'inline-block' }}>✓ {f}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <h4>Available Fleet Listings</h4>
            <div className="grid-cards">
              {vehicles.map((v) => (
                <div key={v.id} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <h3>{v.make} {v.model}</h3>
                    {v.is_ev && <span className="badge badge-ev">⚡ EV</span>}
                  </div>
                  <p style={{ fontSize: '1.2rem', fontWeight: 700, color: '#34d399' }}>${v.price_per_day} <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>/ day</span></p>
                  <button className="btn btn-secondary" onClick={() => inspectVehicle(v)}>Inspect Car Details</button>
                </div>
              ))}
            </div>

            {selectedVehicle && (
              <div className="card" style={{ marginTop: '2rem', border: '1px solid #10b981' }}>
                <h3>Vehicle Details: {selectedVehicle.make} {selectedVehicle.model}</h3>
                {healthScoreData && (
                  <div>
                    <p><strong>Car Health Score (CHS):</strong> {healthScoreData.health_score} / 100 ({healthScoreData.status_summary})</p>
                  </div>
                )}
                {evGuidanceData && (
                  <div style={{ marginTop: '1rem', background: '#0f172a', padding: '1rem', borderRadius: '8px' }}>
                    <p><strong>EV Usable Range:</strong> {evGuidanceData.usable_range_miles} miles</p>
                    <p><strong>Guidance:</strong> {evGuidanceData.guidance_message}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Auth */}
        {activeTab === 'auth' && (
          <div style={{ maxWidth: '450px', margin: '0 auto' }}>
            <div className="card">
              <h3>User Authentication</h3>
              <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required />
                <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required />
                <select value={role} onChange={e => setRole(e.target.value)}>
                  <option value="renter">Renter</option>
                  <option value="host">Host</option>
                  <option value="admin">Admin</option>
                </select>
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Login</button>
                  <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={handleRegister}>Register</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Tab 3: Booking */}
        {activeTab === 'booking' && (
          <div>
            <div className="card" style={{ maxWidth: '600px', margin: '0 auto' }}>
              <h3>Create Booking & Select Extras</h3>
              {!selectedVehicle ? (
                <p style={{ color: '#f59e0b' }}>Please select a vehicle from the Search tab first.</p>
              ) : (
                <form onSubmit={handleCreateBooking} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <p>Selected Car: <strong>{selectedVehicle.make} {selectedVehicle.model}</strong> (${selectedVehicle.price_per_day}/day)</p>
                  <label>Start Date</label>
                  <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} required />
                  <label>End Date</label>
                  <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} required />
                  <label>Participants Count (Cost Split)</label>
                  <input type="number" min="1" max="10" value={participants} onChange={e => setParticipants(e.target.value)} />

                  <label>Bundled Extras</label>
                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <label><input type="checkbox" onChange={e => {
                      if (e.target.checked) setSelectedExtras([...selectedExtras, 'child_seat']);
                      else setSelectedExtras(selectedExtras.filter(x => x !== 'child_seat'));
                    }} /> Child Seat (+$15)</label>
                    <label><input type="checkbox" onChange={e => {
                      if (e.target.checked) setSelectedExtras([...selectedExtras, 'wifi']);
                      else setSelectedExtras(selectedExtras.filter(x => x !== 'wifi'));
                    }} /> Wi-Fi Hotspot (+$10)</label>
                  </div>

                  <button type="submit" className="btn btn-accent">Submit Booking Request</button>
                </form>
              )}
            </div>

            {bookingSuccess && (
              <div className="card" style={{ maxWidth: '600px', margin: '2rem auto', border: '1px solid #34d399' }}>
                <h3>Booking #{bookingSuccess.id} Created!</h3>
                <p>Status: <span className="badge badge-status">{bookingSuccess.status}</span></p>
                <p>Total Price: <strong>${bookingSuccess.total_price}</strong></p>
                <button className="btn btn-primary" onClick={handleProcessPayment}>Pay via Stripe Test Gateway</button>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Telematics & Notifications */}
        {activeTab === 'trip' && (
          <div>
            <div className="card" style={{ maxWidth: '600px', margin: '0 auto' }}>
              <h3>Simulate Live Telematics & Collision Detection</h3>
              <p style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Streams accelerometer/GPS spikes to trigger automated emergency response workflow.</p>
              <button className="btn btn-primary" onClick={handleSimulateTelematics}>Stream Test Telematics Spike</button>

              {telematicsResult && (
                <div style={{ marginTop: '1.5rem', background: '#0f172a', padding: '1rem', borderRadius: '8px' }}>
                  <p><strong>Safety Score:</strong> {telematicsResult.safety_score} / 100</p>
                  <p><strong>Collision Status:</strong> {telematicsResult.collision_detected ? "🚨 COLLISION DETECTED" : "Normal"}</p>
                  {telematicsResult.emergency_event && (
                    <div style={{ background: '#450a0a', padding: '0.8rem', borderRadius: '6px', marginTop: '0.5rem' }}>
                      <p style={{ color: '#fca5a5', fontWeight: 700 }}>EMERGENCY WORKFLOW DISPATCHED</p>
                      <ul>
                        {telematicsResult.emergency_event.actions_taken.map((act, i) => <li key={i} style={{ fontSize: '0.85rem' }}>{act}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="card" style={{ maxWidth: '600px', margin: '2rem auto' }}>
              <h3>System Notifications</h3>
              {notifications.length === 0 ? (
                <p style={{ color: '#94a3b8' }}>No notifications yet.</p>
              ) : (
                <ul style={{ listStyle: 'none' }}>
                  {notifications.map(n => (
                    <li key={n.id} style={{ padding: '0.5rem 0', borderBottom: '1px solid #334155', fontSize: '0.9rem' }}>
                      📩 {n.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
