import React, { createContext, useState, ReactNode } from 'react';

interface BDAContextType {
  selectedProjectArn: string;
  setSelectedProjectArn: (arn: string) => void;
}

export const BDAContext = createContext<BDAContextType>({
  selectedProjectArn: '',
  setSelectedProjectArn: () => {},
});

interface BDAProviderProps {
  children: ReactNode;
}

export const BDAProvider: React.FC<BDAProviderProps> = ({ children }) => {
  const [selectedProjectArn, setSelectedProjectArn] = useState<string>('');

  return (
    <BDAContext.Provider value={{ selectedProjectArn, setSelectedProjectArn }}>
      {children}
    </BDAContext.Provider>
  );
}; 