import React, { useState } from 'react';
import { ArrowLeft, Download, FileCheck, Phone, Mail, Award, AlertCircle, Building2, Calendar, LayoutDashboard, X, User, Briefcase, Clock, ChevronUp, ChevronDown, Filter, Search } from 'lucide-react';

const ScreeningDashboard = ({ results, onBack, onDownload, onConvertToEstuate, onSendInvite }) => {
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [inviteForm, setInviteForm] = useState({
    name: '',
    email: '',
    position: '',
    client: '',
    experience: ''
  });
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [filterConfig, setFilterConfig] = useState({ search: '', minConfidence: 0 });

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilterConfig(prev => ({ ...prev, [name]: value }));
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const filteredAndSortedResults = React.useMemo(() => {
    let resultItems = [...results];

    if (filterConfig.search.trim()) {
      const lowerSearch = filterConfig.search.toLowerCase();
      resultItems = resultItems.filter(item => 
        (item.name || '').toLowerCase().includes(lowerSearch)
      );
    }
    
    if (filterConfig.minConfidence > 0) {
      resultItems = resultItems.filter(item => {
        const score = parseInt(item.confidence_score) || 0;
        return score >= filterConfig.minConfidence;
      });
    }

    if (sortConfig.key !== null) {
      resultItems.sort((a, b) => {
        let aValue = a[sortConfig.key] || '';
        let bValue = b[sortConfig.key] || '';
        
        if (sortConfig.key === 'confidence_score') {
          aValue = parseInt(aValue) || 0;
          bValue = parseInt(bValue) || 0;
        }

        if (aValue < bValue) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    return resultItems;
  }, [results, sortConfig, filterConfig]);

  const openInviteModal = (candidate) => {
    setSelectedCandidate(candidate);
    setInviteForm({
      name: candidate.name || '',
      email: candidate.email || '',
      position: '',
      client: '',
      experience: ''
    });
    setIsInviteModalOpen(true);
  };

  const closeInviteModal = () => {
    setIsInviteModalOpen(false);
    setSelectedCandidate(null);
  };

  const handleInviteSubmit = (e) => {
    e.preventDefault();
    if (onSendInvite) {
      onSendInvite(selectedCandidate, inviteForm);
    }
    closeInviteModal();
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setInviteForm(prev => ({ ...prev, [name]: value }));
  };

  // Confidence score color helper
  const getConfidenceColor = (scoreStr) => {
    const score = parseInt(scoreStr) || 0;
    if (score >= 80) return 'high';
    if (score >= 50) return 'medium';
    return 'low';
  };

  return (
    <div className="screening-dashboard animate-fadeIn">
      {/* Header bar */}
      <div className="dashboard-header glass">
        <div className="header-left">
          <button onClick={onBack} className="back-btn icon-btn" title="Back to Chat">
            <ArrowLeft size={20} />
          </button>
          <div className="header-title">
            <LayoutDashboard size={22} className="title-icon" />
            <div>
              <h1>Screening Report</h1>
              <p>{results.length} Candidates Screened</p>
            </div>
          </div>
        </div>

        <div className="header-actions">
          <button onClick={onDownload} className="download-report-btn primary-btn">
            <Download size={18} />
            Download Excel
          </button>
        </div>
      </div>

      {/* Results Table */}
      <div className="dashboard-content">
        <div className="filter-bar glass" style={{ padding: '1rem 1.25rem', marginBottom: '1.25rem', borderRadius: '12px', display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, border: '1px solid var(--glass-border)', padding: '0.6rem 1rem', borderRadius: '8px', background: '#fff', boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.02)' }}>
             <Search size={16} className="text-muted" />
             <input type="text" name="search" value={filterConfig.search} onChange={handleFilterChange} placeholder="Search candidate by name..." style={{ border: 'none', outline: 'none', flex: 1, fontSize: '0.88rem' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', border: '1px solid var(--glass-border)', padding: '0.6rem 1rem', borderRadius: '8px', background: '#fff', boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.02)' }}>
             <Filter size={16} className="text-muted" />
             <select name="minConfidence" value={filterConfig.minConfidence} onChange={handleFilterChange} style={{ border: 'none', outline: 'none', fontSize: '0.88rem', color: 'var(--text-primary)', background: 'transparent', cursor: 'pointer' }}>
                <option value={0}>All Confidence Scores</option>
                <option value={50}>50+ Score (Medium+)</option>
                <option value={70}>70+ Score (Good+)</option>
                <option value={80}>80+ Score (High)</option>
                <option value={90}>90+ Score (Exceptional)</option>
             </select>
          </div>
        </div>
        
        <div className="table-container glass">
          <table className="screening-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('name')} className="sortable-header">
                  <div className="header-content-wrapper">
                    Candidate Details
                    {sortConfig.key === 'name' && (sortConfig.direction === 'asc' ? <ChevronUp size={14} className="sort-icon" /> : <ChevronDown size={14} className="sort-icon" />)}
                  </div>
                </th>
                <th onClick={() => handleSort('confidence_score')} className="sortable-header">
                  <div className="header-content-wrapper">
                    Confidence
                    {sortConfig.key === 'confidence_score' && (sortConfig.direction === 'asc' ? <ChevronUp size={14} className="sort-icon" /> : <ChevronDown size={14} className="sort-icon" />)}
                  </div>
                </th>
                <th onClick={() => handleSort('experience_comparison')} className="sortable-header">
                  <div className="header-content-wrapper">
                    Experience & Stability
                    {sortConfig.key === 'experience_comparison' && (sortConfig.direction === 'asc' ? <ChevronUp size={14} className="sort-icon" /> : <ChevronDown size={14} className="sort-icon" />)}
                  </div>
                </th>
                <th>All Skills</th>
                <th>Matched Skills</th>
                <th>Gaps & Risks</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedResults.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    No candidates matched your filters.
                  </td>
                </tr>
              ) : (
                filteredAndSortedResults.map((candidate, idx) => (
                <tr key={idx} className="candidate-row">
                  {/* Name & Contact */}
                  <td className="candidate-cell">
                    <div className="candidate-info">
                      <span className="candidate-name">{candidate.name || 'Unknown Candidate'}</span>
                      <div className="contact-links">
                        {candidate.email && (
                          <span title={candidate.email}><Mail size={12} /> {candidate.email}</span>
                        )}
                        {candidate.phone && (
                          <span title={candidate.phone}><Phone size={12} /> {candidate.phone}</span>
                        )}
                      </div>
                      {candidate.last_company && (
                        <div className="last-company">
                          <Building2 size={12} /> {candidate.last_company}
                        </div>
                      )}
                    </div>
                  </td>

                  {/* Confidence Score */}
                  <td>
                    <div className={`confidence-badge ${getConfidenceColor(candidate.confidence_score)}`}>
                      <Award size={14} />
                      {candidate.confidence_score}
                    </div>
                  </td>

                  {/* Experience & Stability */}
                  <td>
                    <div className="exp-stability">
                      <div className="comparison" title="Comparison to JD requirements">
                        {candidate.experience_comparison}
                      </div>
                      <div className="stability-tag">
                        <Calendar size={12} /> {candidate.stability}
                      </div>
                    </div>
                  </td>

                  {/* All Skills */}
                  <td>
                    <div className="skills-cloud">
                      {Array.isArray(candidate.skills) ? (
                        candidate.skills.slice(0, 5).map((skill, sIdx) => (
                          <span key={sIdx} className="skill-tag">{skill}</span>
                        ))
                      ) : (
                        <span className="skill-tag">{candidate.skills}</span>
                      )}
                      {Array.isArray(candidate.skills) && candidate.skills.length > 5 && (
                        <span className="more-skills">+{candidate.skills.length - 5} more</span>
                      )}
                    </div>
                  </td>

                  {/* Matched Skills */}
                  <td>
                    <div className="skills-cloud">
                      {Array.isArray(candidate.matched_skills) ? (
                        candidate.matched_skills.map((skill, sIdx) => (
                          <span key={sIdx} className="skill-tag matched-skill">{skill}</span>
                        ))
                      ) : (
                        candidate.matched_skills ? <span className="skill-tag matched-skill">{candidate.matched_skills}</span> : <span className="text-muted">None</span>
                      )}
                    </div>
                  </td>

                  {/* Gaps & Risks */}
                  <td>
                    <div className="gaps-risks">
                      {candidate.gaps && candidate.gaps !== 'None identified' && (
                        <div className="risk-item" title="Employment/Education Gaps">
                          <AlertCircle size={14} className="risk-icon" />
                          <span>{candidate.gaps}</span>
                        </div>
                      )}
                      {candidate.resume_gaps_against_jd && (
                        <div className="risk-jd-item" title="Gaps against JD">
                          <FileCheck size={14} className="risk-icon" />
                          <span>{candidate.resume_gaps_against_jd}</span>
                        </div>
                      )}
                      {!candidate.gaps && !candidate.resume_gaps_against_jd && (
                        <span className="text-muted">No major risks identified</span>
                      )}
                    </div>
                  </td>

                  {/* Actions */}
                  <td className="actions-cell">
                    <div className="action-buttons" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <button
                        onClick={() => onConvertToEstuate(candidate)}
                        className="convert-btn"
                      >
                        Convert to Estuate Format
                      </button>
                      <button
                        onClick={() => openInviteModal(candidate)}
                        className="invite-btn primary-btn"
                      >
                        Send Interview Invite
                      </button>
                    </div>
                  </td>
                </tr>
              ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invite Modal */}
      {isInviteModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>
                <Calendar size={18} className="title-icon" style={{ marginRight: '8px' }} />
                Schedule Interview
              </h3>
              <button onClick={closeInviteModal} className="icon-btn close-btn" title="Close" type="button">
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleInviteSubmit}>
              <div className="modal-body">
                <div className="input-group">
                  <label>Candidate Name</label>
                  <div className="input-with-icon">
                    <User size={16} className="input-icon" />
                    <input
                      type="text"
                      name="name"
                      value={inviteForm.name}
                      onChange={handleInputChange}
                      required
                      placeholder="Enter candidate name"
                    />
                  </div>
                </div>

                <div className="input-group">
                  <label>Candidate Email</label>
                  <div className="input-with-icon">
                    <Mail size={16} className="input-icon" />
                    <input
                      type="email"
                      name="email"
                      value={inviteForm.email}
                      onChange={handleInputChange}
                      required
                      placeholder="candidate@example.com"
                    />
                  </div>
                </div>

                <div className="input-group">
                  <label>Position</label>
                  <div className="input-with-icon">
                    <Briefcase size={16} className="input-icon" />
                    <input
                      type="text"
                      name="position"
                      value={inviteForm.position}
                      onChange={handleInputChange}
                      required
                      placeholder="e.g. Senior Software Engineer"
                    />
                  </div>
                </div>

                <div className="input-group">
                  <label>Client</label>
                  <div className="input-with-icon">
                    <Building2 size={16} className="input-icon" />
                    <input
                      type="text"
                      name="client"
                      value={inviteForm.client}
                      onChange={handleInputChange}
                      required
                      placeholder="e.g. Estuate Inc"
                    />
                  </div>
                </div>

                <div className="input-group">
                  <label>Years of Experience</label>
                  <div className="input-with-icon">
                    <Clock size={16} className="input-icon" />
                    <input
                      type="number"
                      name="experience"
                      value={inviteForm.experience}
                      onChange={handleInputChange}
                      required
                      min="0"
                      step="0.5"
                      placeholder="e.g. 5"
                    />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={closeInviteModal} className="cancel-btn">
                  Cancel
                </button>
                <button type="submit" className="process-btn">
                  Send Invite
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScreeningDashboard;
