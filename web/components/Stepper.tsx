"use client";

import React, { ReactNode } from "react";
import { motion, AnimatePresence } from "motion/react";
import "./Stepper.css";

export interface StepItem {
  label: string;
  description?: string;
}

export interface StepperProps {
  currentStep: number;
  totalSteps?: number;
  steps: StepItem[];
  onStepChange?: (step: number) => void;
  onNext?: () => void;
  onBack?: () => void;
  nextButtonText?: string;
  backButtonText?: string;
  isNextDisabled?: boolean;
  isBusy?: boolean;
  hideFooter?: boolean;
  className?: string;
  children: ReactNode;
}

export interface StepProps {
  children: ReactNode;
  className?: string;
}

export const Step: React.FC<StepProps> = ({ children, className = "" }) => {
  return <div className={`step-content-pane ${className}`}>{children}</div>;
};

export const Stepper: React.FC<StepperProps> = ({
  currentStep,
  steps,
  onStepChange,
  onNext,
  onBack,
  nextButtonText,
  backButtonText = "← Previous Step",
  isNextDisabled = false,
  isBusy = false,
  hideFooter = false,
  className = "",
  children,
}) => {
  const total = steps.length;
  const progressPercent = total > 1 ? ((currentStep - 1) / (total - 1)) * 100 : 0;

  const handleStepClick = (stepIndex: number) => {
    // Only allow clicking on steps that are completed or current
    if (stepIndex <= currentStep && onStepChange) {
      onStepChange(stepIndex);
    }
  };

  const defaultNextText =
    currentStep === total ? "Complete & Launch Dashboard →" : "Continue →";

  return (
    <div className={`stepper-wrapper ${className}`}>
      {/* ── STEP INDICATOR PROGRESS BAR ────────────────────────── */}
      <div className="stepper-header" role="tablist" aria-label="Registration Progress">
        {/* Background connector track */}
        <div className="stepper-track-bg">
          <div
            className="stepper-track-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Step Nodes */}
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const isActive = stepNumber === currentStep;
          const isCompleted = stepNumber < currentStep;

          return (
            <button
              key={step.label + index}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-label={`Step ${stepNumber}: ${step.label}`}
              disabled={stepNumber > currentStep}
              onClick={() => handleStepClick(stepNumber)}
              className={`step-node-container ${
                isActive ? "active" : isCompleted ? "completed" : "pending"
              }`}
            >
              <div className="step-circle">
                {isCompleted ? (
                  <svg className="w-4 h-4 text-slate-950" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span>{stepNumber}</span>
                )}
              </div>
              <span className="step-label">{step.label}</span>
            </button>
          );
        })}
      </div>

      {/* ── ANIMATED STEP CONTENT ─────────────────────────────── */}
      <div className="stepper-content">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 24, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -24, scale: 0.98 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            className="w-full"
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* ── FOOTER ACTIONS ────────────────────────────────────── */}
      {!hideFooter && (
        <div className="stepper-footer">
          <button
            type="button"
            onClick={onBack}
            disabled={currentStep === 1 || isBusy}
            className="stepper-btn-back"
          >
            {backButtonText}
          </button>

          <button
            type="button"
            onClick={onNext}
            disabled={isNextDisabled || isBusy}
            className="stepper-btn-next"
          >
            {isBusy ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                <span>Processing...</span>
              </span>
            ) : (
              <span>{nextButtonText || defaultNextText}</span>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default Stepper;
