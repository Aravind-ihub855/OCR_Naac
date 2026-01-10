import { useCallback, useState } from 'react';
import { Header, FileUpload, ProgressBar, ExcelPreview, MasterReportView } from '../components';
import { useConversion } from '../hooks';

export function HomePage() {
    const [activeTab, setActiveTab] = useState<'report' | 'excel'>('report');
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);

    const {
        status,
        progress,
        message,
        filename,
        previewData,
        analysisData, // Get analysis data
        convert,
        download,
        reset
    } = useConversion();

    const handleFileSelect = useCallback((file: File) => {
        // Create PDF URL for preview
        const url = URL.createObjectURL(file);
        setPdfUrl(url);
        convert(file);
    }, [convert]);

    const handleReset = useCallback(() => {
        if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        setPdfUrl(null);
        reset();
    }, [pdfUrl, reset]);

    const handleDownloadJson = useCallback(() => {
        if (!analysisData) return;
        const jsonString = JSON.stringify(analysisData, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${(filename || 'document').replace('.pdf', '')}_analysis.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, [analysisData, filename]);

    const isProcessing = status === 'uploading' || status === 'processing';
    const showSplitView = status === 'success';

    return (
        <div className="min-h-screen bg-gray-50 text-gray-900 flex flex-col">
            {/* Header - Compact in Split View */}
            <div className={`relative z-20 bg-white border-b border-gray-200 ${showSplitView ? 'py-2' : ''}`}>
                <Header />
            </div>

            <main className={`flex-1 ${showSplitView ? 'h-[calc(100vh-60px)] overflow-hidden' : 'max-w-5xl mx-auto px-6 py-12 w-full'}`}>

                {/* IDLE / PROCESSING STATE (Centered Layout) */}
                {!showSplitView && (
                    <div className="animate-in fade-in duration-500">
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
                            <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-sm">
                                {!isProcessing ? (
                                    <FileUpload onFileSelect={handleFileSelect} />
                                ) : (
                                    <div className="space-y-6">
                                        <ProgressBar progress={progress} status={message} />
                                    </div>
                                )}
                                {status === 'error' && (
                                    <div className="mt-4 p-4 bg-red-50 text-red-600 rounded-lg text-sm text-center">
                                        {message}
                                        <button onClick={handleReset} className="ml-4 underline font-medium">Try Again</button>
                                    </div>
                                )}
                            </div>
                        </section>
                    </div>
                )}

                {/* SUCCESS STATE (Split View) */}
                {showSplitView && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 h-full">

                        {/* LEFT: PDF Source */}
                        <div className="h-full bg-gray-800 p-4 border-r border-gray-300 hidden lg:block overflow-hidden relative">
                            <div className="absolute top-4 left-4 z-10 bg-black/70 text-white px-3 py-1 rounded-full text-xs font-medium backdrop-blur-sm">
                                Source PDF
                            </div>
                            {pdfUrl && (
                                <iframe
                                    src={`${pdfUrl}#toolbar=0&navpanes=0`}
                                    className="w-full h-full rounded-lg shadow-2xl bg-white"
                                    title="PDF Preview"
                                />
                            )}
                        </div>

                        {/* RIGHT: Extraction Results */}
                        <div className="h-full overflow-y-auto bg-white p-6 scroll-smooth">

                            {/* Actions Bar */}
                            <div className="flex items-center justify-between mb-6 bg-gray-50 p-4 rounded-xl border border-gray-100 sticky top-0 z-30 shadow-sm backdrop-blur-md bg-opacity-90">
                                <div>
                                    <h2 className="font-bold text-gray-800 text-lg leading-tight">{filename}</h2>
                                    <p className="text-xs text-green-600 font-medium flex items-center gap-1">
                                        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                                        Extraction Complete
                                    </p>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={handleDownloadJson}
                                        className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                                    >
                                        JSON
                                    </button>
                                    <button
                                        onClick={download}
                                        className="px-4 py-1.5 text-xs font-bold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-sm transition-all hover:scale-105"
                                    >
                                        Download Excel
                                    </button>
                                    <button
                                        onClick={handleReset}
                                        className="px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                    >
                                        New File
                                    </button>
                                </div>
                            </div>

                            {/* Tabs */}
                            <div className="flex justify-center gap-2 mb-8 bg-gray-100 p-1 rounded-lg w-fit mx-auto">
                                <button
                                    onClick={() => setActiveTab('report')}
                                    className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'report' ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                                >
                                    Digital Master Report
                                </button>
                                <button
                                    onClick={() => setActiveTab('excel')}
                                    className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'excel' ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                                >
                                    Excel Preview
                                </button>
                            </div>

                            {/* View Content */}
                            {activeTab === 'report' && analysisData?.page_elements && (
                                <div className="animate-in slide-in-from-bottom-4 duration-500">
                                    <MasterReportView elements={analysisData.page_elements} />
                                </div>
                            )}

                            {activeTab === 'excel' && previewData.length > 0 && (
                                <div className="animate-in slide-in-from-bottom-4 duration-500">
                                    <ExcelPreview sheets={previewData} />
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
