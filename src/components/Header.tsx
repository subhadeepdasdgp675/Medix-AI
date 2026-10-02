import React, { useState, useEffect, useRef } from 'react';
import { Bell, Search, User, FileText, Pill, Activity } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../lib/api';
import './Header.css';

export function Header() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    
    const timeoutId = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await apiFetch(`/api/cases?limit=20`);
        if (res.ok) {
          const data = await res.json();
          // Filter locally
          const query = searchQuery.toLowerCase();
          const casesArray = Array.isArray(data) ? data : (data.cases || []);
          const results = casesArray.filter((c: any) => 
            (c.patient_name && c.patient_name.toLowerCase().includes(query)) ||
            (c.suspected_disease && c.suspected_disease.toLowerCase().includes(query))
          ).slice(0, 5);
          
          setSearchResults(results);
          setShowResults(true);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setIsSearching(false);
      }
    }, 400);
    
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  const handleResultClick = (caseId: string) => {
    setShowResults(false);
    setSearchQuery('');
    navigate(`/reports?case=${caseId}`);
  };

  return (
    <header className="top-header glass-panel">
      <div className="search-container" ref={searchRef}>
        <Search size={18} className="search-icon" />
        <input 
          type="text" 
          placeholder="Search patients, drugs, or cases..." 
          className="search-input"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onFocus={() => { if (searchQuery.trim()) setShowResults(true); }}
        />
        
        {showResults && searchQuery.trim() && (
          <div className="search-dropdown">
            {isSearching ? (
              <div className="search-loading">Searching...</div>
            ) : searchResults.length > 0 ? (
              searchResults.map((result) => (
                <div 
                  key={result.id} 
                  className="search-dropdown-item"
                  onClick={() => handleResultClick(result.id)}
                >
                  <span className="search-item-title">{result.patient_name || 'Unknown Patient'}</span>
                  <span className="search-item-subtitle">
                    <Activity size={14} /> {result.suspected_disease || 'Pending diagnosis'}
                  </span>
                </div>
              ))
            ) : (
              <div className="search-empty">No results found</div>
            )}
          </div>
        )}
      </div>
      
      <div className="header-actions">
        <button className="action-btn relative">
          <Bell size={20} />
          <span className="notification-dot"></span>
        </button>
        
        <div className="user-profile">
          <div className="avatar">
            <User size={20} />
          </div>
          <div className="user-info">
            <span className="user-name">
              {(() => {
                try {
                  const userStr = localStorage.getItem('medix_user');
                  if (userStr) {
                    const user = JSON.parse(userStr);
                    return user.fullName || user.full_name || user.email || 'Doctor';
                  }
                } catch (e) {}
                return 'Doctor';
              })()}
            </span>
            <span className="user-role">
              {(() => {
                try {
                  const userStr = localStorage.getItem('medix_user');
                  if (userStr) {
                    const user = JSON.parse(userStr);
                    return user.role === 'hospital' ? 'Hospital Admin' : 'Medical Professional';
                  }
                } catch (e) {}
                return 'Medical Professional';
              })()}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
