import React from 'react';
import { ArrowLeft, Download, FileCheck, Phone, Mail, Award, AlertCircle, Building2, Calendar, LayoutDashboard } from 'lucide-react';

const ScreeningDashboard = ({ results, onBack, onDownload, onConvertToEstuate }) => {
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
        <div className="table-container glass">
          <table className="screening-table">
            <thead>
              <tr>
                <th>Candidate Details</th>
                <th>Confidence</th>
                <th>Experience & Stability</th>
                <th>Key Skills Match</th>
                <th>Gaps & Risks</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {results.map((candidate, idx) => (
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

                  {/* Skills */}
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
                    <button 
                      onClick={() => onConvertToEstuate(candidate)}
                      className="convert-btn"
                    >
                      Convert to Estuate Format
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ScreeningDashboard;
