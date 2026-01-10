import { FileText, Image as ImageIcon, PenTool, Layout } from 'lucide-react';
import type { PageElement } from '../types';

interface MasterReportViewProps {
    elements: PageElement[];
}

export function MasterReportView({ elements }: MasterReportViewProps) {
    if (!elements || elements.length === 0) {
        return (
            <div className="text-center p-8 text-gray-500">
                No page elements extracted.
            </div>
        );
    }

    // Sort by order just in case
    const sortedElements = [...elements].sort((a, b) => a.order - b.order);

    return (
        <div className="w-full bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Layout className="w-5 h-5 text-indigo-600" />
                    <h3 className="font-semibold text-gray-800">Master Report (Digital Mirror)</h3>
                </div>
                <span className="text-xs text-indigo-600 bg-indigo-50 px-2 py-1 rounded-full border border-indigo-100">
                    {elements.length} Elements
                </span>
            </div>

            <div className="p-8 space-y-8 bg-white min-h-[600px]">
                {sortedElements.map((element, index) => (
                    <div key={index} className="w-full animate-in fade-in slide-in-from-bottom-2 duration-500" style={{ animationDelay: `${index * 50}ms` }}>
                        {renderElement(element)}
                    </div>
                ))}
            </div>
        </div>
    );
}

function renderElement(element: PageElement) {
    switch (element.type) {
        case 'logo':
            return (
                <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-indigo-100 rounded-lg bg-indigo-50/30">
                    <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-3">
                        <ImageIcon className="w-8 h-8 text-indigo-600" />
                    </div>
                    <span className="text-sm font-medium text-gray-900">{element.content || 'Logo Detected'}</span>
                    <span className="text-xs text-gray-500">Position: {element.position || 'Header'}</span>
                </div>
            );

        case 'metadata':
            return (
                <div className="flex items-start gap-4 p-4 bg-gray-50 border-1 border-gray-100 rounded-lg">
                    <div className="p-2 bg-white rounded shadow-sm">
                        <FileText className="w-4 h-4 text-gray-400" />
                    </div>
                    <div>
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{element.key}</span>
                        <p className="text-lg font-medium text-gray-900 mt-1">{element.value}</p>
                    </div>
                </div>
            );

        case 'heading':
            return (
                <div className="text-center py-4">
                    <h2 className="text-2xl font-bold text-gray-900">{element.content}</h2>
                    <div className="h-1 w-24 bg-indigo-600 mx-auto mt-2 rounded-full opacity-20"></div>
                </div>
            );

        case 'text_block':
            return (
                <div className="prose max-w-none text-gray-700 leading-relaxed p-2">
                    <p>{element.content}</p>
                </div>
            );

        case 'table':
            // Simple HTML table render for now (or could reuse a Table component)
            const cols = element.columns || [];
            const rows = element.rows || [];
            if (cols.length === 0) return null;

            return (
                <div className="border border-gray-200 rounded-lg overflow-hidden my-4">
                    <div className="bg-gray-100 px-4 py-2 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase flex justify-between">
                        <span>{element.table_name || 'Table'}</span>
                        {element.table_heading && <span className="text-gray-500 font-normal normal-case">{element.table_heading}</span>}
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="text-xs text-gray-700 uppercase bg-gray-50">
                                <tr>
                                    {cols.map((col: any, i: number) => (
                                        <th key={i} className="px-6 py-3 border-b">{col.name}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((row: any, i: number) => (
                                    <tr key={i} className="bg-white border-b hover:bg-gray-50">
                                        {cols.map((col: any, j: number) => (
                                            <td key={j} className="px-6 py-4 max-w-xs truncate">
                                                {row.data[col.name]}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            );

        case 'signature':
            return (
                <div className="flex flex-col items-end mt-12 mb-6 mr-12">
                    <div className="w-64 border-t-2 border-gray-800 pt-4 text-center">
                        <div className="mb-2 flex justify-center text-indigo-600">
                            <PenTool className="w-6 h-6" />
                        </div>
                        <p className="text-lg font-bold text-gray-900 font-serif italic">
                            {element.signer_name || '(Signature)'}
                        </p>
                        <p className="text-sm text-gray-500 font-medium uppercase tracking-wide mt-1">
                            {element.designation}
                        </p>
                    </div>
                </div>
            );

        default:
            return (
                <div className="p-4 border border-gray-200 rounded text-gray-400 text-sm">
                    Unknown Element: {element.type}
                </div>
            );
    }
}
