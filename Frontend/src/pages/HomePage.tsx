import { useCallback } from 'react';
import { Header, FileUpload, ProgressBar, ResultCard } from '../components';
import { useConversion } from '../hooks';

export function HomePage() {
    const {
        status,
        progress,
        message,
        filename,
        convert,
        download,
        reset
    } = useConversion();

    const handleFileSelect = useCallback((file: File) => {
        convert(file);
    }, [convert]);

    const isProcessing = status === 'uploading' || status === 'processing';

    return (
        <div className="min-h-screen bg-white text-gray-900">
            {/* Content */}
            <div className="relative z-10">
                <Header />

                <main className="max-w-4xl mx-auto px-6 py-12">
                    {/* Hero Section */}
                    <section className="text-center mb-12">
                        <h1 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">
                            Convert PDF to Excel
                        </h1>
                        <p className="text-lg text-gray-500 max-w-2xl mx-auto">
                            Extract tables from any PDF document using AI.
                        </p>
                    </section>

                    {/* Upload Section */}
                    <section className="mb-8">
                        <div className="bg-gray-50 border border-gray-200 rounded-2xl p-8">
                            {status === 'idle' ? (
                                <FileUpload onFileSelect={handleFileSelect} />
                            ) : (
                                <div className="space-y-6">
                                    {isProcessing && (
                                        <ProgressBar
                                            progress={progress}
                                            status={message}
                                        />
                                    )}

                                    <ResultCard
                                        status={status}
                                        filename={filename}
                                        message={message}
                                        onDownload={download}
                                        onReset={reset}
                                    />
                                </div>
                            )}
                        </div>
                    </section>
                </main>

                {/* Footer */}
                <footer className="border-t border-gray-200 mt-2">
                    <div className="max-w-6xl mx-auto px-6 py-8 text-center text-sm text-gray-400">
                        <p>PDF2Excel - Intelligent Document Extraction</p>
                    </div>
                </footer>
            </div>
        </div>
    );
}
