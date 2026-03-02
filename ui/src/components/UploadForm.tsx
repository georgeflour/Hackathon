"use client";
import { useRef } from "react";

interface Props { onUpload: (file: File) => void }

export default function UploadForm({ onUpload }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  }

  return (
    <div
      className="border-2 border-dashed border-blue-300 rounded-xl p-10 text-center cursor-pointer
                 hover:border-blue-500 hover:bg-blue-50 transition-colors"
      onClick={() => inputRef.current?.click()}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
    >
      <div className="text-4xl mb-3">📄</div>
      <p className="text-gray-700 font-medium">Drop your electricity bill here</p>
      <p className="text-gray-400 text-sm mt-1">or click to browse — PNG, JPG, PDF supported</p>
      <input
        ref={inputRef}
        type="file"
        accept="image/*,.pdf"
        className="hidden"
        onChange={handleChange}
      />
    </div>
  );
}

