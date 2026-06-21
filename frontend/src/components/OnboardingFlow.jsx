import React, { useState } from 'react';
import { supabase } from '../supabaseClient';
import { useAuth } from '../context/AuthContext';

const STEPS = [
  {
    id: 'goal',
    question: 'What do you want to learn?',
    subtext: 'Be specific — the more detail you give, the more personalized your path will be.',
    type: 'textarea',
    placeholder: 'e.g. I want to understand Machine Learning and build my own models from scratch',
    field: 'learning_goal',
  },
  {
    id: 'background',
    question: 'What is your current background?',
    subtext: 'This helps us start at the right level for you.',
    type: 'select',
    field: 'background',
    options: [
      { value: 'complete_beginner', label: '🌱 Complete beginner — just starting out' },
      { value: 'some_experience', label: '📚 Some experience — know the basics' },
      { value: 'intermediate', label: '⚡ Intermediate — comfortable but want to go deeper' },
      { value: 'advanced', label: '🚀 Advanced — want to master edge cases and nuances' },
    ],
  },
  {
    id: 'style',
    question: 'How do you learn best?',
    subtext: 'We will tune the lesson format to match your style.',
    type: 'cards',
    field: 'learning_style',
    options: [
      { value: 'visual', label: '👁️ Visual', desc: 'Diagrams, charts, analogies' },
      { value: 'reading', label: '📖 Reading', desc: 'In-depth explanations and text' },
      { value: 'hands-on', label: '🔨 Hands-on', desc: 'Code examples and exercises' },
      { value: 'mixed', label: '🎯 Mixed', desc: 'A bit of everything' },
    ],
  },
  {
    id: 'time',
    question: 'How much time can you dedicate daily?',
    subtext: 'Even 15 minutes a day compounds significantly over time.',
    type: 'slider',
    field: 'daily_time_budget_minutes',
    min: 10,
    max: 120,
    step: 5,
    default: 30,
  },
];

export default function OnboardingFlow({ onComplete }) {
  const { user, session } = useAuth();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({
    learning_goal: '',
    background: '',
    learning_style: '',
    daily_time_budget_minutes: 30,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const current = STEPS[step];
  const isLastStep = step === STEPS.length - 1;

  const handleChange = (field, value) => {
    setAnswers(prev => ({ ...prev, [field]: value }));
  };

  const isStepValid = () => {
    const val = answers[current.field];
    if (current.type === 'textarea' || current.type === 'select') return val && val.trim() !== '';
    if (current.type === 'cards') return val !== '';
    if (current.type === 'slider') return typeof val === 'number';
    return true;
  };

  const handleNext = () => {
    if (isLastStep) {
      handleSubmit();
    } else {
      setStep(s => s + 1);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      const { error: dbError } = await supabase
        .from('user_profiles')
        .update({
          learning_goals: [answers.learning_goal],
          background: answers.background,
          learning_style: answers.learning_style,
          daily_time_budget_minutes: answers.daily_time_budget_minutes,
        })
        .eq('id', user.id);

      if (dbError) throw dbError;
      onComplete();
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
      setSubmitting(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
    }}>
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '640px',
          padding: '3rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '2rem',
        }}
      >
        {/* Progress dots */}
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
          {STEPS.map((s, i) => (
            <div
              key={s.id}
              style={{
                width: i === step ? '2rem' : '0.5rem',
                height: '0.5rem',
                borderRadius: '99px',
                background: i <= step ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.15)',
                transition: 'all 0.4s ease',
              }}
            />
          ))}
        </div>

        {/* Question */}
        <div style={{ textAlign: 'center' }}>
          <h2
            className="gradient-text"
            style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.5rem' }}
          >
            {current.question}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            {current.subtext}
          </p>
        </div>

        {/* Input */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

          {current.type === 'textarea' && (
            <textarea
              rows={4}
              placeholder={current.placeholder}
              value={answers[current.field]}
              onChange={e => handleChange(current.field, e.target.value)}
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '12px',
                padding: '1rem',
                color: 'white',
                fontSize: '1rem',
                resize: 'vertical',
                outline: 'none',
                fontFamily: 'inherit',
                transition: 'border-color 0.2s',
              }}
              onFocus={e => e.target.style.borderColor = 'var(--accent-cyan)'}
              onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
            />
          )}

          {current.type === 'select' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {current.options.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => handleChange(current.field, opt.value)}
                  style={{
                    padding: '1rem 1.25rem',
                    background: answers[current.field] === opt.value
                      ? 'rgba(6, 182, 212, 0.15)'
                      : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${answers[current.field] === opt.value
                      ? 'var(--accent-cyan)'
                      : 'rgba(255,255,255,0.08)'}`,
                    borderRadius: '10px',
                    color: 'white',
                    textAlign: 'left',
                    cursor: 'pointer',
                    fontSize: '0.95rem',
                    transition: 'all 0.2s',
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          {current.type === 'cards' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              {current.options.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => handleChange(current.field, opt.value)}
                  style={{
                    padding: '1.25rem',
                    background: answers[current.field] === opt.value
                      ? 'rgba(6, 182, 212, 0.15)'
                      : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${answers[current.field] === opt.value
                      ? 'var(--accent-cyan)'
                      : 'rgba(255,255,255,0.08)'}`,
                    borderRadius: '12px',
                    color: 'white',
                    cursor: 'pointer',
                    textAlign: 'center',
                    transition: 'all 0.2s',
                  }}
                >
                  <div style={{ fontSize: '1.5rem', marginBottom: '0.4rem' }}>{opt.label.split(' ')[0]}</div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{opt.label.split(' ').slice(1).join(' ')}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '0.25rem' }}>{opt.desc}</div>
                </button>
              ))}
            </div>
          )}

          {current.type === 'slider' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
              <div
                className="gradient-text"
                style={{ fontSize: '3rem', fontWeight: 700 }}
              >
                {answers[current.field]} min
              </div>
              <input
                type="range"
                min={current.min}
                max={current.max}
                step={current.step}
                value={answers[current.field]}
                onChange={e => handleChange(current.field, parseInt(e.target.value))}
                style={{
                  width: '100%',
                  accentColor: 'var(--accent-cyan)',
                  cursor: 'pointer',
                }}
              />
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                width: '100%',
                color: 'var(--text-secondary)',
                fontSize: '0.8rem',
              }}>
                <span>{current.min} min</span>
                <span>{current.max} min</span>
              </div>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div style={{
            padding: '0.75rem 1rem',
            background: 'rgba(239,68,68,0.15)',
            border: '1px solid rgba(239,68,68,0.4)',
            borderRadius: '8px',
            color: '#fca5a5',
            fontSize: '0.9rem',
          }}>
            {error}
          </div>
        )}

        {/* Navigation */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            onClick={() => setStep(s => s - 1)}
            disabled={step === 0}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'transparent',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '10px',
              color: step === 0 ? 'rgba(255,255,255,0.2)' : 'var(--text-secondary)',
              cursor: step === 0 ? 'default' : 'pointer',
              fontSize: '0.9rem',
              transition: 'all 0.2s',
            }}
          >
            ← Back
          </button>

          <button
            onClick={handleNext}
            disabled={!isStepValid() || submitting}
            style={{
              padding: '0.75rem 2rem',
              background: isStepValid() && !submitting
                ? 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))'
                : 'rgba(255,255,255,0.05)',
              border: 'none',
              borderRadius: '10px',
              color: isStepValid() && !submitting ? 'white' : 'rgba(255,255,255,0.3)',
              cursor: isStepValid() && !submitting ? 'pointer' : 'default',
              fontWeight: 600,
              fontSize: '1rem',
              transition: 'all 0.3s',
              boxShadow: isStepValid() && !submitting ? '0 0 20px rgba(6,182,212,0.3)' : 'none',
            }}
          >
            {submitting ? 'Saving...' : isLastStep ? '🚀 Start Learning' : 'Continue →'}
          </button>
        </div>
      </div>
    </div>
  );
}
