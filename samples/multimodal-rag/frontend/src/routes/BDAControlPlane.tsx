import { listBlueprints, listProjects, createBlueprint, createProject, uploadDocument, BlueprintListRequest, ProjectListRequest } from "@/lib/api";
import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// Define the Blueprint interface based on the actual response structure
interface Blueprint {
  blueprintArn: string;
  blueprintStage: 'DEVELOPMENT' | 'LIVE';
  // Optional fields that might not be present in all responses
  blueprintVersion?: string;
  blueprintName?: string;
  creationTime?: string;
  lastModifiedTime?: string;
}

interface ApiResponse<T> {
  response: string;
  data?: T;
  [key: string]: unknown;
}

interface BlueprintResponse {
  blueprintArn?: string;
  blueprintStage?: 'DEVELOPMENT' | 'LIVE';
  blueprintVersion?: string;
  blueprintName?: string;
  creationTime?: string;
  lastModifiedTime?: string;
}

interface BlueprintListResponse {
  blueprints: BlueprintResponse[];
}

interface ProjectResponse {
  projectArn?: string;
  projectStage?: 'DEVELOPMENT' | 'LIVE';
  projectName?: string;
  creationTime?: string;
}

interface ProjectListResponse {
  projects: ProjectResponse[];
}

// Define the Project interface based on the actual response structure
interface Project {
  projectArn: string;
  projectStage: 'DEVELOPMENT' | 'LIVE';
  projectName: string;
  creationTime: string;
}

export default function BDAControlPlane() {
  const [loading, setLoading] = useState(false);
  const [loadingOperation, setLoadingOperation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Blueprint creation state
  const [blueprintName, setBlueprintName] = useState<string>('');
  const [createBlueprintStage, setCreateBlueprintStage] = useState<'DEVELOPMENT' | 'LIVE'>('LIVE');
  const [blueprintType, setBlueprintType] = useState<'DOCUMENT' | 'IMAGE'>('DOCUMENT');
  const [schemaFileName, setSchemaFileName] = useState<string>('');
  // Schema fields for defining data extraction rules in the blueprint
  const [schemaFields, setSchemaFields] = useState<Array<{
    name: string;         // Unique identifier for the field
    description: string;  // Description of what data should be extracted
    type: string;        // Data type (e.g., 'string', 'number', 'array')
    inferenceType: string; // Type of inference to perform (e.g., 'text', 'table', 'key-value')
  }>>([{ name: '', description: '', type: 'string', inferenceType: 'Explicit' }]);

  // Project creation state
  const [projectName, setProjectName] = useState<string>('');
  const [createProjectStage, setCreateProjectStage] = useState<'DEVELOPMENT' | 'LIVE'>('LIVE');
  const [projectModality, setProjectModality] = useState<'document' | 'image' | 'video' | 'audio'>('document');

  // Add state for blueprints
  const [blueprints, setBlueprints] = useState<Blueprint[]>([]);
  const [selectedBlueprintArn, setSelectedBlueprintArn] = useState<string>('');
  
  // Add state for projects
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectArn, setSelectedProjectArn] = useState<string>('');
  
  // Add state for project inputs
  const [projectArn, setProjectArn] = useState<string>('');
  const [projectStage, setProjectStage] = useState< 'LIVE' | 'DEVELOPMENT'>('LIVE');
  
  // Add state for blueprint inputs for list projects
  const [blueprintArnForProjects, setBlueprintArnForProjects] = useState<string>('');
  const [blueprintStageForProjects, setBlueprintStageForProjects] = useState<'DEVELOPMENT' | 'LIVE'>('LIVE');
  
  const handleCreateBlueprint = async () => {
    setLoading(true);
    setLoadingOperation('createBlueprint');
    setError(null);
    setSuccessMessage(null);
    try {
      // If schema file is uploaded, use that, otherwise use schema fields
      if (schemaFileName) {
        await createBlueprint({
          operation: 'CREATE',
          blueprint_name: blueprintName,
          blueprint_stage: createBlueprintStage,
          blueprint_type: blueprintType,
          schema_file_name: schemaFileName
        });
      } else {
        // Filter out empty schema fields
        const validSchemaFields = schemaFields.filter(field => 
          field.name.trim() !== '' && field.description.trim() !== '' && field.type.trim() !== '' && field.inferenceType.trim() !== ''
        );

        if (validSchemaFields.length === 0) {
          throw new Error("Please either upload a schema file or add schema fields");
        }

        // Create blueprint with schema fields
        await createBlueprint({
          operation: 'CREATE',
          blueprint_name: blueprintName,
          blueprint_stage: createBlueprintStage,
          blueprint_type: blueprintType,
          schema_fields: validSchemaFields
        });
      }

      setSuccessMessage('Blueprint created successfully');
      // Refresh the blueprints list
      handleListBlueprints();
    } catch (e) {
      setError("Failed to create blueprint.");
      console.error(e);
    } finally {
      setLoading(false);
      setLoadingOperation(null);
    }
  };

  const handleCreateProject = async () => {
    setLoading(true);
    setLoadingOperation('createProject');
    setError(null);
    setSuccessMessage(null);

    try {
      const projectData: any = {
        operation: 'CREATE',
        projectName,
        projectStage: createProjectStage,
        blueprint_arn: selectedBlueprintArn,
        modality: projectModality,
      };

      // Add standard output configuration for image modality
      if (projectModality === 'image') {
        projectData.standardOutputConfiguration = {
          image: {
            extraction: {
              category: {
                state: 'ENABLED',
                types: ['TEXT_DETECTION']
              },
              boundingBox: {
                state: 'ENABLED'
              }
            },
            generativeField: {
              state: 'ENABLED',
              types: ['IMAGE_SUMMARY']
            }
          }
        };
      }
      
      // Add standard output configuration for video modality
      if (projectModality === 'video') {
        projectData.standardOutputConfiguration = {
          video: {
            extraction: {
              category: {
                state: 'ENABLED',
                types: ['TEXT_DETECTION']
              },
              boundingBox: {
                state: 'ENABLED'
              }
            },
            generativeField: {
              state: 'ENABLED',
              types: ['VIDEO_SUMMARY', 'CHAPTER_SUMMARY']
            }
          }
        };
      }

      await createProject(projectData);
      setSuccessMessage('Project created successfully');
      // Refresh the projects list
      handleListProjects();
    } catch (e) {
      setError("Failed to create project.");
      console.error(e);
    } finally {
      setLoading(false);
      setLoadingOperation(null);
    }
  };

  const handleListBlueprints = async () => {
    setLoading(true);
    setLoadingOperation('list');
    setError(null);
    try {
      const request: BlueprintListRequest = {
        operation: 'LIST'
      };

      if (projectArn && projectArn !== 'Enter the project ARN') {
        request.projectFilter = {
          projectArn: projectArn,
          projectStage: projectStage
        };
      }

      const response = (await listBlueprints(request)) as ApiResponse<BlueprintListResponse>;
      
      if (response && typeof response === 'object' && 'response' in response && typeof response.response === 'string') {
        try {
          const parsedNestedResponse = JSON.parse(response.response) as BlueprintListResponse;
          if (parsedNestedResponse?.blueprints) {
            processBlueprints(parsedNestedResponse.blueprints);
          }
        } catch (parseError) {
          console.error(parseError);
          setError("Failed to parse blueprints response.");
        }
      } else if (typeof response === 'string') {
        try {
          const parsedResponse = JSON.parse(response) as BlueprintListResponse;
          if (parsedResponse?.blueprints) {
            processBlueprints(parsedResponse.blueprints);
          }
        } catch (parseError) {
          console.error(parseError);
          setError("Failed to parse blueprints response.");
        }
      } else if (response && typeof response === 'object') {
        const blueprintsResponse = response as unknown as BlueprintListResponse;
        if (blueprintsResponse.blueprints) {
          processBlueprints(blueprintsResponse.blueprints);
        }
      }
    } catch (e) {
      setError("Failed to list blueprints.");
      console.error(e);
    } finally {
      setLoading(false);
      setLoadingOperation(null);
    }
  };
  
  const processBlueprints = (blueprintsArray: BlueprintResponse[]) => {
    const processedBlueprints: Blueprint[] = [];
    
    for (const item of blueprintsArray) {
      if (item && typeof item === 'object') {
        const blueprint: Blueprint = {
          blueprintArn: typeof item.blueprintArn === 'string' ? item.blueprintArn : '',
          blueprintStage: (item.blueprintStage === 'DEVELOPMENT' || item.blueprintStage === 'LIVE') 
            ? item.blueprintStage 
            : 'DEVELOPMENT'
        };
        
        if (item.blueprintName) {
          blueprint.blueprintName = item.blueprintName;
        } else {
          const arnParts = blueprint.blueprintArn.split('/');
          const extractedName = arnParts.length > 1 ? arnParts[arnParts.length - 1] : blueprint.blueprintArn;
          blueprint.blueprintName = extractedName;
        }
        
        if (typeof item.blueprintVersion === 'string') {
          blueprint.blueprintVersion = item.blueprintVersion;
        }
        
        if (typeof item.creationTime === 'string') {
          blueprint.creationTime = item.creationTime;
        }
        
        if (typeof item.lastModifiedTime === 'string') {
          blueprint.lastModifiedTime = item.lastModifiedTime;
        }
        
        processedBlueprints.push(blueprint);
      }
    }
    
    setBlueprints(processedBlueprints);
    
    if (processedBlueprints.length > 0) {
      setSelectedBlueprintArn(processedBlueprints[0].blueprintArn);
    }
  };

  const handleListProjects = async () => {
    setLoading(true);
    setLoadingOperation('listProjects');
    setError(null);
    try {
      const request: ProjectListRequest = {
        operation: 'LIST'
      };

      if (blueprintArnForProjects) {
        request.blueprintFilter = {
          blueprintArn: blueprintArnForProjects,
          blueprintStage: blueprintStageForProjects
        };
      }

      const response = (await listProjects(request)) as ApiResponse<ProjectListResponse>;
      
      if (response && typeof response === 'object' && 'response' in response && typeof response.response === 'string') {
        try {
          const parsedNestedResponse = JSON.parse(response.response) as ProjectListResponse;
          if (parsedNestedResponse?.projects) {
            processProjects(parsedNestedResponse.projects);
          }
        } catch (parseError) {
          console.error(parseError);
          setError("Failed to parse projects response.");
        }
      } else {
        setError("Unexpected response format from projects API.");
      }
    } catch (e) {
      setError("Failed to list projects.");
      console.error(e);
    } finally {
      setLoading(false);
      setLoadingOperation(null);
    }
  };
  
  const processProjects = (projectsArray: ProjectResponse[]) => {
    const processedProjects: Project[] = [];
    
    for (const item of projectsArray) {
      if (item && typeof item === 'object') {
        const project: Project = {
          projectArn: typeof item.projectArn === 'string' ? item.projectArn : '',
          projectStage: (item.projectStage === 'DEVELOPMENT' || item.projectStage === 'LIVE') 
            ? item.projectStage 
            : 'DEVELOPMENT',
          projectName: typeof item.projectName === 'string' ? item.projectName : 'Unnamed Project',
          creationTime: typeof item.creationTime === 'string' ? item.creationTime : ''
        };
        
        processedProjects.push(project);
      }
    }
    
    setProjects(processedProjects);
    
    if (processedProjects.length > 0) {
      setSelectedProjectArn(processedProjects[0].projectArn);
      localStorage.setItem('selectedProjectArn', processedProjects[0].projectArn);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">BDA Control Plane</h1>
      <div className="bg-white p-6 rounded-lg shadow">
        {/* Main Container - Split into Left (Create) and Right (List) */}
        <div className="grid grid-cols-2 gap-8">
          {/* Left Column - Create Operations */}
          <div>
            <h2 className="text-lg font-medium mb-4">Create Operations</h2>
            
            {/* Create Blueprint Card */}
            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 mb-8 min-h-[450px]">
              <h3 className="text-sm font-medium mb-4">Create Blueprint</h3>
              <div className="space-y-4">
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="blueprintName">Blueprint Name</Label>
                  <Input
                    id="blueprintName"
                    value={blueprintName}
                    onChange={(e) => setBlueprintName(e.target.value)}
                    placeholder="Enter blueprint name"
                    className="w-full"
                  />
                </div>
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="blueprintStage">Blueprint Stage</Label>
                  <Select 
                    value={createBlueprintStage} 
                    onValueChange={(value) => setCreateBlueprintStage(value as 'DEVELOPMENT' | 'LIVE')}
                  >
                    <SelectTrigger id="blueprintStage" className="w-full">
                      <SelectValue placeholder="Select blueprint stage" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DEVELOPMENT">DEVELOPMENT</SelectItem>
                      <SelectItem value="LIVE">LIVE</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="blueprintType">Blueprint Type</Label>
                  <Select 
                    value={blueprintType} 
                    onValueChange={(value) => setBlueprintType(value as 'DOCUMENT' | 'IMAGE')}
                  >
                    <SelectTrigger id="blueprintType" className="w-full">
                      <SelectValue placeholder="Select blueprint type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DOCUMENT">DOCUMENT</SelectItem>
                      <SelectItem value="IMAGE">IMAGE</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Upload Schema Section */}
                <div className="grid w-full items-center gap-1.5">
                  <Label>Upload Schema</Label>
                  <div className="flex gap-2">
                    <Input
                      type="file"
                      accept=".json"
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          try {
                            setLoading(true);
                            setLoadingOperation('uploadSchema');
                            await new Promise((resolve, reject) => {
                              const reader = new FileReader();
                              reader.onload = async (event) => {
                                try {
                                  const content = event.target?.result as string;
                                  JSON.parse(content);
                                  const blob = new Blob([content], { type: 'application/json' });
                                  await uploadDocument(blob, file.name);
                                  setSchemaFileName(file.name);
                                  setSuccessMessage('Schema file uploaded successfully');
                                  resolve(null);
                                } catch (e) {
                                  reject(e);
                                }
                              };
                              reader.onerror = () => reject(reader.error);
                              reader.readAsText(file);
                            });
                          } catch (e) {
                            setError("Failed to upload schema file.");
                            console.error(e);
                          } finally {
                            setLoading(false);
                            setLoadingOperation(null);
                          }
                        }
                      }}
                      className="w-full"
                      disabled={loading}
                    />
                  </div>
                  {schemaFileName && (
                    <p className="text-sm text-gray-500 mt-1">
                      Selected file: {schemaFileName}
                    </p>
                  )}
                </div>

                <div>
                  <Button 
                    onClick={handleCreateBlueprint}
                    className="w-full border-2 border-blue-500 text-blue-500 bg-transparent py-2 px-4 rounded hover:bg-blue-500 hover:text-white mt-4"
                    disabled={loading || !blueprintName}
                  >
                    {loadingOperation === 'createBlueprint' ? 'Creating Blueprint...' : 'Create Blueprint'}
                  </Button>
                  {successMessage && successMessage.includes('Blueprint') && (
                    <p className="text-green-500 mt-2 text-sm text-center">{successMessage}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Create Project Card */}
            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 min-h-[450px]">
              <h3 className="text-sm font-medium mb-4">Create Project</h3>
              <div className="space-y-4">
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="projectName">Project Name</Label>
                  <Input
                    id="projectName"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="Enter project name"
                    className="w-full"
                  />
                </div>
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="createProjectStage">Project Stage</Label>
                  <Select 
                    value={createProjectStage} 
                    onValueChange={(value) => setCreateProjectStage(value as 'DEVELOPMENT' | 'LIVE')}
                  >
                    <SelectTrigger id="createProjectStage" className="w-full">
                      <SelectValue placeholder="Select project stage" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DEVELOPMENT">DEVELOPMENT</SelectItem>
                      <SelectItem value="LIVE">LIVE</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="projectModality">Modality</Label>
                  <Select 
                    value={projectModality} 
                    onValueChange={(value) => setProjectModality(value as 'document' | 'image' | 'video' | 'audio')}
                  >
                    <SelectTrigger id="projectModality" className="w-full">
                      <SelectValue placeholder="Select modality" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="document">Document</SelectItem>
                      <SelectItem value="image">Image</SelectItem>
                      <SelectItem value="video">Video</SelectItem>
                      <SelectItem value="audio">Audio</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Button 
                    onClick={handleCreateProject}
                    className="w-full border-2 border-blue-500 text-blue-500 bg-transparent py-2 px-4 rounded hover:bg-blue-500 hover:text-white mt-4"
                    // disabled={loading || !projectName || !selectedBlueprintArn}
                    disabled={loading || !projectName}
                  >
                    {loadingOperation === 'createProject' ? 'Creating Project...' : 'Create Project'}
                  </Button>
                  {successMessage && successMessage.includes('Project') && (
                    <p className="text-green-500 mt-2 text-sm text-center">{successMessage}</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - List Operations */}
          <div>
            <h2 className="text-lg font-medium mb-4">List Operations</h2>
            
            {/* List Blueprint Card */}
            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 mb-8 min-h-[450px]">
              <h3 className="text-sm font-medium mb-4">List Blueprints</h3>
              <div className="space-y-4">
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="projectArn">Project ARN</Label>
                  <Input
                    id="projectArn"
                    value={projectArn}
                    onChange={(e) => setProjectArn(e.target.value)}
                    placeholder="Enter project ARN"
                    className="w-full"
                  />
                </div>
                
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="projectStage">Project Stage</Label>
                  <Select 
                    value={projectStage} 
                    onValueChange={(value) => setProjectStage(value as 'LIVE' | 'DEVELOPMENT')}
                  >
                    <SelectTrigger id="projectStage" className="w-full">
                      <SelectValue placeholder="Select project stage" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DEVELOPMENT">DEVELOPMENT</SelectItem>
                      <SelectItem value="LIVE">LIVE</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <Button 
                  onClick={handleListBlueprints} 
                  className="w-full border-2 border-green-500 text-green-500 bg-transparent py-2 px-4 rounded hover:bg-green-500 hover:text-white"
                  disabled={loading}
                >
                  {loadingOperation === 'list' ? 'Loading Blueprints...' : 'List Blueprints'}
                </Button>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Select Blueprint {blueprints.length === 0 && "(No blueprints available)"}
                  </label>
                  <Select 
                    value={selectedBlueprintArn} 
                    onValueChange={setSelectedBlueprintArn}
                    disabled={blueprints.length === 0}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select a blueprint" />
                    </SelectTrigger>
                    <SelectContent>
                      {blueprints.map((blueprint) => (
                        <SelectItem 
                          key={blueprint.blueprintArn} 
                          value={blueprint.blueprintArn}
                        >
                          {blueprint.blueprintName || blueprint.blueprintArn}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* List Projects Card */}
            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 min-h-[450px]">
              <h3 className="text-sm font-medium mb-4">List Projects</h3>
              <div className="space-y-4">
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="blueprintArnForProjects">(Optional) Blueprint ARN</Label>
                  <Input
                    id="blueprintArnForProjects"
                    value={blueprintArnForProjects}
                    onChange={(e) => setBlueprintArnForProjects(e.target.value)}
                    placeholder="(Optional) Enter blueprint ARN"
                    className="w-full"
                  />
                </div>
                
                <div className="grid w-full items-center gap-1.5">
                  <Label htmlFor="blueprintStageForProjects">(Optional) Blueprint Stage</Label>
                  <Select 
                    value={blueprintStageForProjects} 
                    onValueChange={(value) => setBlueprintStageForProjects(value as 'DEVELOPMENT' | 'LIVE')}
                  >
                    <SelectTrigger id="blueprintStageForProjects" className="w-full">
                      <SelectValue placeholder="Select blueprint stage" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DEVELOPMENT">DEVELOPMENT</SelectItem>
                      <SelectItem value="LIVE">LIVE</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <Button 
                  onClick={handleListProjects} 
                  className="w-full border-2 border-green-500 text-green-500 bg-transparent py-2 px-4 rounded hover:bg-green-500 hover:text-white"
                  disabled={loading}
                >
                  {loadingOperation === 'listProjects' ? 'Loading Projects...' : 'List Projects'}
                </Button>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Select Project {projects.length === 0 && "(No projects available)"}
                  </label>
                  <Select 
                    value={selectedProjectArn} 
                    onValueChange={(value) => {
                      setSelectedProjectArn(value);
                      localStorage.setItem('selectedProjectArn', value);
                    }}
                    disabled={projects.length === 0}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select a project" />
                    </SelectTrigger>
                    <SelectContent>
                      {projects.map((project) => (
                        <SelectItem 
                          key={project.projectArn} 
                          value={project.projectArn}
                        >
                          {project.projectName} ({project.projectStage})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </div>
        </div>

        {error && <p className="text-red-500 mt-4">{error}</p>}
      </div>
    </div>
  );
}
