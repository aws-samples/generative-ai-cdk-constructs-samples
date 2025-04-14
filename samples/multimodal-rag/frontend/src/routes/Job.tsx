//
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
// with the License. A copy of the License is located at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
// OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
// and limitations under the License.
//

import { useParams, useLoaderData, Await } from "react-router-dom";
import { Suspense, useState } from "react";
import { Job } from "../types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../components/ui/tooltip";
import { Skeleton } from "../components/ui/skeleton";
import { Document, Page, pdfjs } from "react-pdf";
import { Box, ColumnLayout } from "@cloudscape-design/components";
import JobDetail from "../components/jobs/JobDetail";

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export default function Jobs() {
  const params = useParams();
  const loaderData = useLoaderData() as { job: Job };
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  const getFileNameWithoutExtension = (s3Key: string) => {
    const parts = s3Key.split('/');
    const fileName = parts[parts.length - 1];
    return fileName.split('.').slice(0, -1).join('.');
  };

  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-6">
        <Card>
          <CardHeader>
            <CardTitle>
              <Suspense fallback={<Skeleton className="h-6 bg-slate-200" />}>
                <Await
                  resolve={loaderData.job}
                  errorElement={<p>An error occurred while loading.</p>}
                >
                  {(loadedData) => (
                    <div className="flex justify-between gap-4">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className="truncate leading-relaxed">
                              {getFileNameWithoutExtension(loadedData.demo_metadata.file.s3_key)}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{loadedData.id}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                        {loadedData.demo_metadata.job_status}
                      </span>
                    </div>
                  )}
                </Await>
              </Suspense>
            </CardTitle>
            <CardDescription className="pt-2">
              <span className="mr-2 inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold text-foreground transition-colors">
                Job ID:
              </span>
              <span className="font-mono text-xs">{params.jobId}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="max-h-[calc(100vh-16rem)] overflow-y-auto">
            <Suspense fallback={<Skeleton className="h-[600px]" />}>
              <Await
                resolve={loaderData.job}
                errorElement={<p>An error occurred while loading.</p>}
              >
                {(loadedData) => (
                  <div className="space-y-2">
                    {/* Document Preview Section */}
                    <div className="space-y-2">
                      <div className="flex justify-center border rounded-lg p-2 bg-white">
                        {/* PDF Preview */}
                        {loadedData.demo_metadata.file.s3_key.toLowerCase().endsWith('.pdf') && (
                          <>
                            <Document
                              file={loadedData.demo_metadata.file.presigned_url}
                              onLoadSuccess={onDocumentLoadSuccess}
                              className="max-w-full"
                            >
                              <Page pageNumber={pageNumber} />
                            </Document>
                            <div className="flex justify-center items-center gap-4 mt-2">
                              <button
                                onClick={() => setPageNumber(page => Math.max(page - 1, 1))}
                                disabled={pageNumber <= 1}
                                className="px-3 py-1 border rounded-md disabled:opacity-50"
                              >
                                Previous
                              </button>
                              <span>
                                Page {pageNumber} of {numPages}
                              </span>
                              <button
                                onClick={() => setPageNumber(page => Math.min(page + 1, numPages || 1))}
                                disabled={pageNumber >= (numPages || 1)}
                                className="px-3 py-1 border rounded-md disabled:opacity-50"
                              >
                                Next
                              </button>
                            </div>
                          </>
                        )}

                        {/* Image Preview */}
                        {/\.(png|jpg|jpeg|svg)$/i.test(loadedData.demo_metadata.file.s3_key) && (
                          <img 
                            src={loadedData.demo_metadata.file.presigned_url}
                            alt="Document preview"
                            className="max-w-full max-h-[600px] object-contain"
                          />
                        )}

                        {/* Video Preview */}
                        {/\.(mov|mp4|webm|ogg)$/i.test(loadedData.demo_metadata.file.s3_key) && (
                          <video
                            src={loadedData.demo_metadata.file.presigned_url}
                            controls
                            className="max-w-full max-h-[600px]"
                          >
                            Your browser does not support the video tag.
                          </video>
                        )}

                        {/* Audio Preview */}
                        {/\.(mp3|wav|ogg|m4a)$/i.test(loadedData.demo_metadata.file.s3_key) && (
                          <div className="w-full max-w-[600px] p-4">
                            <div className="bg-gray-100 p-4 rounded-lg">
                              <div className="text-center mb-4">
                                <span className="text-lg font-medium">Audio Player</span>
                              </div>
                              <audio
                                src={loadedData.demo_metadata.file.presigned_url}
                                controls
                                className="w-full"
                              >
                                Your browser does not support the audio tag.
                              </audio>
                            </div>
                          </div>
                        )}

                        {/* Office Documents Preview (PowerPoint and Word) */}
                        {/\.(ppt|pptx|doc|docx)$/i.test(loadedData.demo_metadata.file.s3_key) && (
                          <iframe
                            src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(loadedData.demo_metadata.file.presigned_url)}`}
                            width="100%"
                            height="600"
                            frameBorder="0"
                            title="Office document preview"
                          />
                        )}

                        {/* Unsupported File Type Message */}
                        {!/\.(pdf|png|jpg|jpeg|svg|ppt|pptx|doc|docx|mov|mp4|webm|ogg|mp3|wav|m4a)$/i.test(loadedData.demo_metadata.file.s3_key) && (
                          <div className="p-4 text-center text-gray-500">
                            Preview not available for this file type
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Basic Metadata */}
                    <ColumnLayout columns={3} variant="text-grid">
                      <div>
                        <Box variant="awsui-key-label">Status</Box>
                        <div>{loadedData.demo_metadata.job_status}</div>
                      </div>
                      <div>
                        <Box variant="awsui-key-label">Requested At</Box>
                        <div>{new Date(loadedData.demo_metadata.requested_at).toLocaleString()}</div>
                      </div>
                      <div>
                        <Box variant="awsui-key-label">Completed At</Box>
                        <div>{loadedData.demo_metadata.completed_at ? new Date(loadedData.demo_metadata.completed_at).toLocaleString() : 'N/A'}</div>
                      </div>
                    </ColumnLayout>

                    {/* Document Links */}
                    {loadedData.demo_metadata.result_file && (
                      <div className="flex items-center gap-4 mt-4">
                        <a 
                          href={loadedData.demo_metadata.result_file.presigned_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 underline"
                        >
                          Download Standard Output
                        </a>
                        {loadedData.demo_metadata.custom_output_file?.presigned_url && (
                          <a 
                            href={loadedData.demo_metadata.custom_output_file.presigned_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 underline"
                          >
                            Download Custom Output
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </Await>
            </Suspense>
          </CardContent>
        </Card>
      </div>
      <div className="col-span-6">
        <Card>
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
          </CardHeader>
          <CardContent className="max-h-[calc(100vh-16rem)] overflow-y-auto">
            <Suspense fallback={<Skeleton className="h-[600px]" />}>
              <Await
                resolve={loaderData.job}
                errorElement={<p>An error occurred while loading.</p>}
              >
                {(loadedData) => <JobDetail job={loadedData} />}
              </Await>
            </Suspense>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
