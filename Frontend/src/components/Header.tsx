import { FileSpreadsheet } from 'lucide-react';

export function Header() {
    return (
        <header className="w-full py-6 px-8 border-b border-gray-200">
            <div className="max-w-6xl mx-auto flex items-center justify-center">
                {/* Logo */}
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-gray-900 rounded-xl">
                        <FileSpreadsheet className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-gray-900">AI Document Extractor</h1>
                    </div>
                </div>
            </div>
        </header>
    );
}
