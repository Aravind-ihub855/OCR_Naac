import { useState } from 'react';
import { Table, ChevronLeft, ChevronRight } from 'lucide-react';

export interface SheetData {
    name: string;
    data: string[][];
}

interface ExcelPreviewProps {
    sheets: SheetData[];
}

export function ExcelPreview({ sheets }: ExcelPreviewProps) {
    const [activeSheet, setActiveSheet] = useState(0);

    if (!sheets || sheets.length === 0) {
        return null;
    }

    const currentSheet = sheets[activeSheet];
    const hasMultipleSheets = sheets.length > 1;

    return (
        <div className="w-full space-y-4">
            {/* Sheet Navigation */}
            {hasMultipleSheets && (
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        {sheets.map((sheet, index) => (
                            <button
                                key={index}
                                onClick={() => setActiveSheet(index)}
                                className={`
                  px-4 py-2 text-sm font-medium rounded-lg transition-all
                  ${activeSheet === index
                                        ? 'bg-gray-900 text-white'
                                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                    }
                `}
                            >
                                {sheet.name}
                            </button>
                        ))}
                    </div>

                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => setActiveSheet(Math.max(0, activeSheet - 1))}
                            disabled={activeSheet === 0}
                            className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="text-sm text-gray-500 px-2">
                            {activeSheet + 1} / {sheets.length}
                        </span>
                        <button
                            onClick={() => setActiveSheet(Math.min(sheets.length - 1, activeSheet + 1))}
                            disabled={activeSheet === sheets.length - 1}
                            className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}

            {/* Table Container */}
            <div className="border border-gray-200 rounded-xl overflow-hidden">
                {/* Table Header Info */}
                <div className="px-5 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Table className="w-4 h-4 text-gray-400" />
                        <span className="font-medium text-gray-700">{currentSheet.name}</span>
                    </div>
                    <span className="text-sm text-gray-400">
                        {currentSheet.data.length - 1} rows × {currentSheet.data[0]?.length || 0} columns
                    </span>
                </div>

                {/* Scrollable Table */}
                <div className="overflow-auto max-h-[400px]">
                    {currentSheet.data.length > 0 ? (
                        <table className="w-full">
                            <thead>
                                <tr className="bg-gray-50">
                                    {currentSheet.data[0]?.map((header, colIndex) => (
                                        <th
                                            key={colIndex}
                                            className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200 whitespace-nowrap sticky top-0 bg-gray-50"
                                        >
                                            {header || `Col ${colIndex + 1}`}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {currentSheet.data.slice(1).map((row, rowIndex) => (
                                    <tr
                                        key={rowIndex}
                                        className="hover:bg-gray-50/50 transition-colors"
                                    >
                                        {row.map((cell, colIndex) => (
                                            <td
                                                key={colIndex}
                                                className="px-5 py-3 text-sm text-gray-700 whitespace-nowrap"
                                            >
                                                {cell || <span className="text-gray-300">—</span>}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <div className="p-12 text-center text-gray-400">
                            No data available
                        </div>
                    )}
                </div>
            </div>

            {/* Info Footer */}
            <p className="text-xs text-gray-400 text-center">
                Showing preview • Download for full data
            </p>
        </div>
    );
}
