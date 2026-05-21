import React from 'react';
import { FileText, Download, Eye, File } from 'lucide-react';

const ConvertedResumes = ({ resumes, onPreview, onDownload }) => {
  return (
    <div className="screening-dashboard animate-fadeIn" style={{ padding: '2rem' }}>
      <div className="dashboard-header glass" style={{ marginBottom: '2rem' }}>
        <div className="header-title">
          <FileText size={22} className="title-icon" />
          <div>
            <h1>Converted Resumes</h1>
            <p>{resumes.length} Formatting Jobs</p>
          </div>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="table-container glass">
          {resumes.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              <FileText size={48} style={{ opacity: 0.2, margin: '0 auto 1rem auto' }} />
              <h3>No Resumes Converted Yet</h3>
              <p>Go to a screening report and click "Convert to Estuate Format" to format a resume.</p>
            </div>
          ) : (
            <table className="screening-table">
              <thead>
                <tr>
                  <th>Candidate Name</th>
                  <th>Template</th>
                  <th>Converted On</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {resumes.map((resume, idx) => (
                  <tr key={idx} className="candidate-row">
                    <td>
                      <div className="candidate-info">
                        <span className="candidate-name">{resume.candidateName}</span>
                        <div className="contact-links" style={{ marginTop: '0.25rem' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                             <File size={12} /> {resume.originalFile}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="skill-tag" style={{ background: 'var(--primary-light)', color: 'var(--primary-dark)' }}>
                        {resume.templateName}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: 'var(--text-muted)' }}>{resume.date}</span>
                    </td>
                    <td className="actions-cell">
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button 
                          onClick={() => onPreview(resume)}
                          className="convert-btn"
                          style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-main)' }}
                        >
                          <Eye size={14} /> Preview
                        </button>
                        <button 
                          onClick={() => onDownload(resume)}
                          className="convert-btn"
                          style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                        >
                          <Download size={14} /> Download
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConvertedResumes;
