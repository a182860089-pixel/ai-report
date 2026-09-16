"use client";

import { useState } from "react";
import type { Text } from "@/data/types";
import { T } from "@/components/Text";

export function Banner({
  kind,
  children
}: {
  kind: "error" | "ok";
  children: React.ReactNode;
}) {
  return (
    <p className={`desk-banner ${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </p>
  );
}

export function Stamp({ status }: { status: "draft" | "published" }) {
  return (
    <span className={`desk-stamp ${status}`}>
      {status === "published" ? <T zh="付印" en="Live" /> : <T zh="校样" en="Draft" />}
    </span>
  );
}

export function Field({
  label,
  hint,
  children
}: {
  label: React.ReactNode;
  hint?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <label className="desk-field">
      <span className="desk-label">{label}</span>
      {children}
      {hint ? <span className="desk-hint">{hint}</span> : null}
    </label>
  );
}

export function TextPair({
  label,
  value,
  onChange,
  multiline = false,
  rows = 3
}: {
  label: React.ReactNode;
  value: Text;
  onChange: (next: Text) => void;
  multiline?: boolean;
  rows?: number;
}) {
  return (
    <fieldset className="desk-pair">
      <legend>{label}</legend>
      <div className="desk-pair-grid">
        <label>
          <span>中</span>
          {multiline ? (
            <textarea rows={rows} value={value.zh} onChange={(event) => onChange({ ...value, zh: event.currentTarget.value })} />
          ) : (
            <input value={value.zh} onChange={(event) => onChange({ ...value, zh: event.currentTarget.value })} />
          )}
        </label>
        <label>
          <span>EN</span>
          {multiline ? (
            <textarea rows={rows} value={value.en} onChange={(event) => onChange({ ...value, en: event.currentTarget.value })} />
          ) : (
            <input value={value.en} onChange={(event) => onChange({ ...value, en: event.currentTarget.value })} />
          )}
        </label>
      </div>
    </fieldset>
  );
}

export function PairList({
  label,
  items,
  onChange,
  rows = 3
}: {
  label: React.ReactNode;
  items: Text[];
  onChange: (next: Text[]) => void;
  rows?: number;
}) {
  return (
    <div className="desk-stack">
      <div className="desk-row-head">
        <h3>{label}</h3>
        <button
          type="button"
          className="desk-btn ghost"
          onClick={() => onChange([...items, { zh: "", en: "" }])}
        >
          <T zh="加一段" en="Add" />
        </button>
      </div>
      {items.length === 0 ? (
        <p className="desk-hint">
          <T zh="空列表可以提交。" en="Empty list is allowed." />
        </p>
      ) : null}
      {items.map((item, index) => (
        <div className="desk-block" key={index}>
          <div className="desk-row-head">
            <span className="desk-kicker">{index + 1}</span>
            <button
              type="button"
              className="desk-btn ghost danger"
              onClick={() => onChange(items.filter((_, i) => i !== index))}
            >
              <T zh="删" en="Remove" />
            </button>
          </div>
          <TextPair label={`#${index + 1}`} value={item} onChange={(next) => {
            const copy = items.slice();
            copy[index] = next;
            onChange(copy);
          }} multiline rows={rows} />
        </div>
      ))}
    </div>
  );
}

export function ConfirmButton({
  label,
  confirm,
  onConfirm,
  disabled,
  className
}: {
  label: React.ReactNode;
  confirm: React.ReactNode;
  onConfirm: () => void | Promise<void>;
  disabled?: boolean;
  className?: string;
}) {
  const [armed, setArmed] = useState(false);
  return (
    <button
      type="button"
      disabled={disabled}
      className={className}
      onClick={async () => {
        if (!armed) {
          setArmed(true);
          return;
        }
        await onConfirm();
        setArmed(false);
      }}
      onBlur={() => setArmed(false)}
    >
      {armed ? confirm : label}
    </button>
  );
}

export function asErrorMessage(error: unknown) {
  if (error && typeof error === "object" && "message" in error && typeof error.message === "string") {
    return error.message;
  }
  return "Request failed.";
}