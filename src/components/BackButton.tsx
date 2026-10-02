import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export function BackButton({ className = '' }: { className?: string }) {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate(-1)}
      className={`btn-back ${className}`}
      title="Go back to previous section"
      type="button"
    >
      <ArrowLeft size={16} />
      <span>Back</span>
    </button>
  );
}
