import { useCallback } from 'react';
import { Header, FileUpload, ProgressBar, ResultCard, ExcelPreview } from '../components';
import { useConversion } from '../hooks';

export function HomePage() {
    const {
        status,
        progress,
        message,
        filename,
        previewData,
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
            <div className="relative z-10">
                <Header />

                <main className="max-w-5xl mx-auto px-6 py-12">
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

                    {/* Excel Preview Section */}
                    {status === 'success' && previewData.length > 0 && (
                        <section className="mb-8">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4">
                                Preview
                            </h2>
                            <ExcelPreview sheets={previewData} />
                        </section>
                    )}
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
