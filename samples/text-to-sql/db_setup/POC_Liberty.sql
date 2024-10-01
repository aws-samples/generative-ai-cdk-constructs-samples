/*******************************************************************************
   Drop database if it exists
********************************************************************************/
DROP DATABASE IF EXISTS `HESAMPLE`;


/*******************************************************************************
   Create database
********************************************************************************/
CREATE DATABASE `HESAMPLE`;

USE `HESAMPLE`;


CREATE TABLE `POC_QuestionText`(
	`QuesID` int NOT NULL,
	`Text` varchar(30) NOT NULL,
      `Year` int NOT NULL,
 CONSTRAINT `PK_QuestionText` PRIMARY KEY (`QuesID`)
);


CREATE TABLE `POC_Question`(
	`QuesID` int  NOT NULL,
	`QuestionType` int NOT NULL,
 CONSTRAINT `PK_POC_Question` PRIMARY KEY  (`QuesID`)
);


CREATE TABLE `POC_QuestionType`(
	`QuesTypeID` int NOT NULL,
	`Name` varchar(25) NULL,
 CONSTRAINT `PK_POC_QuestionType_ID` PRIMARY KEY (
	`QuesTypeID` 
)
);


CREATE TABLE `POC_MCOAnswer`(
	`MCOAnswerID` int  NOT NULL,
	`QuesID` int NOT NULL,
	`Correct` int NOT NULL,
	`Text` varchar(30) NOT NULL,
 CONSTRAINT `PK_POC_MCOAnswer` PRIMARY KEY (`MCOAnswerID`)
);

create table `Student`
(
    `studentID` numeric not null
        primary key,
    `firstname` varchar(255),
    `lastname`  varchar(255),
    `dob`       datetime
);


create table`Address`
(
    `studentID`         numeric,
    `contactname`       varchar(255),
    `relationship`     varchar(50),
    `number`            varchar(50),
    `street`            varchar(50),
    `city`              varchar(35),
    `state`             varchar(50),
    `zip`               varchar(50),
    `liveshere`         varchar(2),
    `mailhere`          varchar(2),
    `homephoneareacode` varchar(50),
    `homephone`         varchar(50),
    `email1`            varchar(50)
);

create table `StudentYear`
(
    `studentID` numeric,
    `yearId`    int,
    `isActive`  varchar(2)
);

ALTER TABLE `Address` ADD CONSTRAINT `FK_Address_Student`
    FOREIGN KEY (`studentID`) REFERENCES `Student` (`studentID`) ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE `StudentYear` ADD CONSTRAINT `FK_StudentYear_Student`
    FOREIGN KEY (`studentID`) REFERENCES `Student` (`studentID`) ON DELETE NO ACTION ON UPDATE NO ACTION;

-- ALTER TABLE `POC_MCOAnswer`
-- ADD CONSTRAINT `FK_POC_MCOAnswer_QuesID`
-- FOREIGN KEY (`QuesID`) REFERENCES `POC_Question`(`QuesID`);


-- ALTER TABLE `POC_Question`
-- ADD CONSTRAINT `FK_POC_Question_QuestionType`
-- FOREIGN KEY (`QuestionType`) REFERENCES `POC_QuestionType`(`QuesTypeID`);


-- ALTER TABLE `POC_QuestionText`
-- ADD CONSTRAINT `FK_POC_QuestionText_QuesID`
-- FOREIGN KEY (`QuesID`) REFERENCES `POC_Question`(`QuesID`);


INSERT INTO `POC_QuestionType`
           (`QuesTypeID`
           ,`Name`)
     VALUES
           ('1'
           ,'Multiple Choice'),
            ('2'
           ,'Single Choice');


INSERT INTO `POC_Question`
           (`QuesID`,
           `QuestionType`)
     VALUES
           ('1',
           '1'),
           ('2',
           '2'),
           ('3',
           '1'),
           ('4',
           '1');



INSERT INTO `POC_QuestionText`
           (`QuesID`
           ,`Text`,
           `Year`)
     VALUES
           ('1'
           ,'What color is the sky?',
           '2019'),
           ('2'
           ,'What color is the grass?',
           '2024'),
           ('3'
           ,'What color is the sun?',
           '2024'),
           ('4'
           ,'What color is the ocean?',
           '2023');

INSERT INTO `POC_MCOAnswer`
           (`MCOAnswerID`
           ,`QuesID`
           ,`Correct`
           ,`Text`)
     VALUES
           ('1',
           '1',
           '0',
           '<p>Light Blue</p>'),
           ('2',
           '2',
           '1',
           '<p>Green</p>'),
           ('3',
           '3',
           '2',
           '<p>Yellow</p>'),
           ('4',
           '4',
           '3',
           '<p>Blue</p>');


INSERT INTO `Student` (`studentID`, `firstname`, `lastname`, `dob`)
VALUES
    (1, 'Mickey', 'Mouse', '1928-11-18'),
    (2, 'Minnie', 'Mouse', '1928-11-18'),
    (3, 'Donald', 'Duck', '1934-06-09'),
    (4, 'Daisy', 'Duck', '1940-01-09'),
    (5, 'Goofy', 'Goof', '1932-05-25'),
    (6, 'Pluto', NULL, '1930-09-05'),
    (7, 'Mickey', 'Mouse', '1928-11-18'),
    (8, 'Bugs', 'Bunny', '1940-07-27'),
    (9, 'Porky', 'Pig', '1935-03-02'),
    (10, 'Daffy', 'Duck', '1937-04-17'),
    (11, 'Scooby', 'Doo', '1969-09-13'),
    (12, 'Shaggy', 'Rogers', '1969-09-13'),
    (13, 'Fred', 'Flintstone', '1960-09-30'),
    (14, 'Wilma', 'Flintstone', '1960-09-30'),
    (15, 'Barney', 'Rubble', '1960-09-30'),
    (16, 'Betty', 'Rubble', '1960-09-30'),
    (17, 'George', 'Jetson', '1962-09-23'),
    (18, 'Jane', 'Jetson', '1962-09-23'),
    (19, 'Elroy', 'Jetson', '1962-09-23'),
    (20, 'Judy', 'Jetson', '1962-09-23'),
    (21, 'Popeye', NULL, '1929-01-17'),
    (22, 'Olive', 'Oyl', '1919-12-19'),
    (23, 'Bluto', NULL, NULL),
    (24, 'SpongeBob', 'SquarePants', '1999-05-01'),
    (25, 'Patrick', 'Star', '1999-05-01'),
    (26, 'Squidward', 'Tentacles', '1999-05-01'),
    (27, 'Sandy', 'Cheeks', '1999-05-01'),
    (28, 'Tom', 'Cat', NULL),
    (29, 'Jerry', 'Mouse', NULL),
    (30, 'Bart', 'Simpson', '1987-04-19'),
    (31, 'Homer', 'Simpson', '1987-04-19'),
    (32, 'Marge', 'Simpson', '1987-04-19'),
    (33, 'Lisa', 'Simpson', '1987-04-19'),
    (34, 'Maggie', 'Simpson', '1987-04-19'),
    (35, 'Peter', 'Griffin', '1999-01-31'),
    (36, 'Lois', 'Griffin', '1999-01-31'),
    (37, 'Meg', 'Griffin', '1999-01-31'),
    (38, 'Chris', 'Griffin', '1999-01-31'),
    (39, 'Stewie', 'Griffin', '1999-01-31'),
    (40, 'Brian', 'Griffin', '1999-01-31'),
    (41, 'Eric', 'Cartman', NULL),
    (42, 'Stan', 'Marsh', NULL),
    (43, 'Kyle', 'Broflovski', NULL),
    (44, 'Kenny', 'McCormick', NULL),
    (45, 'Randy', 'Marsh', NULL),
    (46, 'Shrek', NULL, '2001-05-22'),
    (47, 'Fiona', 'Shrek', '2001-05-22'),
    (48, 'Donkey', NULL, '2001-05-22'),
    (49, 'Puss', 'Boots', '2004-11-05'),
    (50, 'Felix', 'the Cat', '1919-11-09');

INSERT INTO `Address`
 (`studentID`, `contactname`, `relationship`, `number`,
  `street`, `city`, `state`, `zip`, `liveshere`, `mailhere`,
   `homephoneareacode`, `homephone`, `email1`)
VALUES
    (1, 'Walt Disney Studios', 'Parent', '500', 'Burbank Blvd', 'Burbank', 'CA', '91521', 1, 1, '818', '555-1234', 'mickey@disney.com'),
    (2, 'Walt Disney Studios', 'Parent', '500', 'Burbank Blvd', 'Burbank', 'CA', '91521', 1, 1, '818', '555-1234', 'minnie@disney.com'),
    (3, 'Daisy Duck', 'Parent', '321', 'Duck Pond Ln', 'Duckburg', 'AZ', '54321', 1, 1, '555', '123-4567', 'donald@ducks.com'),
    (4, 'Donald Duck', 'Parent', '321', 'Duck Pond Ln', 'Duckburg', 'AZ', '54321', 1, 1, '555', '123-4567', 'daisy@ducks.com'),
    (5, 'Goofy Goof', 'Friend', '742', 'Silly St', 'Toontown', 'CA', '98765', 1, 0, '909', '987-6543', 'goofy@toons.com'),
    (6, 'Pluto Dog', 'Pet', NULL, 'Kennel Rd', 'Dogtown', 'CA', '87654', 1, 0, '909', '234-5678', 'pluto@dogs.com'),
    (7, 'Walt Disney Studios', 'Parent', '500', 'Burbank Blvd', 'Burbank', 'CA', '91521', 1, 1, '818', '555-1234', 'mickey@disney.com'),
    (8, 'Warner Bros Studios', 'Parent', '4000', 'Warner Blvd', 'Los Angeles', 'CA', '90068', 1, 1, '310', '555-5678', 'bugs@warnerbros.com'),
    (9, 'Warner Bros Studios', 'Parent', '4000', 'Warner Blvd', 'Los Angeles', 'CA', '90068', 1, 1, '310', '555-5678', 'porky@warnerbros.com'),
    (10, 'Warner Bros Studios', 'Parent', '4000', 'Warner Blvd', 'Los Angeles', 'CA', '90068', 1, 1, '310', '555-5678', 'daffy@warnerbros.com'),
    (11, 'Mystery Inc', 'Friend', '222', 'Haunted House Ln', 'Coolsville', 'OH', '54321', 1, 0, '555', '987-6543', 'scooby@mysteryinc.com'),
    (12, 'Mystery Inc', 'Friend', '222', 'Haunted House Ln', 'Coolsville', 'OH', '54321', 1, 0, '555', '987-6543', 'shaggy@mysteryinc.com'),
    (13, 'Bedrock City Hall', 'Parent', '301', 'Granite St', 'Bedrock', 'AZ', '65432', 1, 1, '555', '321-7654', 'fred@bedrock.com'),
    (14, 'Bedrock City Hall', 'Parent', '301', 'Granite St', 'Bedrock', 'AZ', '65432', 1, 1, '555', '321-7654', 'wilma@bedrock.com'),
    (15, 'Bedrock City Hall', 'Friend', '301', 'Granite St', 'Bedrock', 'AZ', '65432', 1, 0, '555', '321-7654', 'barney@bedrock.com'),
    (16, 'Bedrock City Hall', 'Friend', '301', 'Granite St', 'Bedrock', 'AZ', '65432', 1, 0, '555', '321-7654', 'betty@bedrock.com'),
    (17, 'Spacely Sprockets', 'Parent', '100', 'Skypad Apartments', 'Orbit City', 'FL', '32100', 1, 1, '555', '456-7890', 'george@orbitcity.com'),
    (18, 'Spacely Sprockets', 'Parent', '100', 'Skypad Apartments', 'Orbit City', 'FL', '32100', 1, 1, '555', '456-7890', 'jane@orbitcity.com'),
    (19, 'Spacely Sprockets', 'Parent', '100', 'Skypad Apartments', 'Orbit City', 'FL', '32100', 1, 1, '555', '456-7890', 'elroy@orbitcity.com'),
    (20, 'Spacely Sprockets', 'Parent', '100', 'Skypad Apartments', 'Orbit City', 'FL', '32100', 1, 1, '555', '456-7890', 'judy@orbitcity.com'),
    (21, 'Popeye Village', 'Parent', '123', 'Spinach Ave', 'Sweethaven', 'CA', '54321', 1, 1, '555', '987-6543', 'popeye@spinach.com'),
    (22, 'Olive Oyl', 'Friend', '456', 'Olive St', 'Sweethaven', 'CA', '54321', 1, 0, '555', '567-8901', 'olive@spinach.com'),
    (23, 'Salty Sailor Pub', 'Friend', '789', 'Main St', 'Sweethaven', 'CA', '54321', 1, 0, '555', '234-5678', 'bluto@spinach.com'),
    (24, 'Pineapple Under the Sea', 'Parent', '124', 'Bikini Bottom', 'Pacific Ocean', 'NA', '12345', 1, 1, '555', '555-1234', 'spongebob@sea.com'),
    (25, 'Pineapple Under the Sea', 'Parent', '124', 'Bikini Bottom', 'Pacific Ocean', 'NA', '12345', 1, 1, '555', '555-1234', 'patrick@sea.com'),
    (26, 'Squidward''s Tiki Hut', 'Friend', '126', 'Annoyance Ln', 'Bikini Bottom', 'Pacific Ocean', 'NA', 1, 0, '555', '555-5678', 'squidward@sea.com'),
    (27, 'Treasure Island', 'Parent', '456', 'Sandy Way', 'Bikini Bottom', 'Pacific Ocean', 'NA', 1, 1, '555', '987-6543', 'sandy@sea.com'),
    (28, 'Mouse Hole', 'Friend', '321', 'Cheese St', 'Mouseville', 'NA', '98765', 1, 0, '555', '876-5432', 'tom@mouse.com'),
    (29, 'Mouse Hole', 'Friend', '321', 'Cheese St', 'Mouseville', 'NA', '98765', 1, 0, '555', '876-5432', 'jerry@mouse.com'),
    (30, '742 Evergreen Terrace', 'Parent', '1', 'Main St', 'Springfield', 'NA', '98765', 1, 1, '555', '123-4567', 'bart@springfield.com'),
    (31, '742 Evergreen Terrace', 'Parent', '1', 'Main St', 'Springfield', 'NA', '98765', 1, 1, '555', '123-4567', 'homer@springfield.com'),
    (32, '742 Evergreen Terrace', 'Parent', '1', 'Main St', 'Springfield', 'NA', '98765', 1, 1, '555', '123-4567', 'marge@springfield.com'),
    (33, '742 Evergreen Terrace', 'Parent', '1', 'Main St', 'Springfield', 'NA', '98765', 1, 1, '555', '123-4567', 'lisa@springfield.com'),
    (34, '742 Evergreen Terrace', 'Parent', '1', 'Main St', 'Springfield', 'NA', '98765', 1, 1, '555', '123-4567', 'maggie@springfield.com'),
    (35, '31 Spooner St', 'Friend', '2', 'Main St', 'Quahog', 'RI', '02910', 1, 0, '401', '555-7890', 'peter@quahog.com'),
    (36, '31 Spooner St', 'Friend', '2', 'Main St', 'Quahog', 'RI', '02910', 1, 0, '401', '555-7890', 'lois@quahog.com'),
    (37, '31 Spooner St', 'Friend', '2', 'Main St', 'Quahog', 'RI', '02910', 1, 0, '401', '555-7890', 'meg@quahog.com'),
    (38, '31 Spooner St', 'Friend', '2', 'Main St', 'Quahog', 'RI', '02910', 1, 0, '401', '555-7890', 'chris@quahog.com'),
    (39, '31 Spooner St', 'Friend', '2', 'Main St', 'Quahog', 'RI', '02910', 1, 0, '401', '555-7890', 'stewie@quahog.com'),
    (40, '31 Spooner St', 'Friend', '2', 'Main St', 'Quahog', 'RI', '02910', 1, 0, '401', '555-7890', 'brian@quahog.com'),
    (41, 'South Park Elementary', 'Friend', '1234', 'South Park Ave', 'South Park', 'CO', '80440', 1, 0, '555', '234-5678', 'eric@southpark.com'),
    (42, 'South Park Elementary', 'Friend', '1234', 'South Park Ave', 'South Park', 'CO', '80440', 1, 0, '555', '234-5678', 'stan@southpark.com'),
    (43, 'South Park Elementary', 'Friend', '1234', 'South Park Ave', 'South Park', 'CO', '80440', 1, 0, '555', '234-5678', 'kyle@southpark.com'),
    (44, 'South Park Elementary', 'Friend', '1234', 'South Park Ave', 'South Park', 'CO', '80440', 1, 0, '555', '234-5678', 'kenny@southpark.com'),
    (45, 'City Hall', 'Parent', '555', 'Main St', 'South Park', 'CO', '80440', 1, 1, '555', '987-6543', 'randy@southpark.com'),
    (46, 'Swamp', 'Friend', '1', 'Ogre Rd', 'Duloc', 'NA', '54321', 1, 0, '555', '555-4321', 'shrek@farfaraway.com'),
    (47, 'Swamp', 'Parent', '1', 'Ogre Rd', 'Duloc', 'NA', '54321', 1, 1, '555', '555-4321', 'fiona@farfaraway.com'),
    (48, 'Swamp', 'Friend', '1', 'Ogre Rd', 'Duloc', 'NA', '54321', 1, 0, '555', '555-4321', 'donkey@farfaraway.com'),
    (49, 'Puss', 'Parent', '1', 'Boots Ln', 'Far Far Away', 'NA', '12345', 1, 1, '555', '123-4567', 'puss@farfaraway.com'),
    (50, 'Felix', 'Friend', '1', 'Cat Alley', 'Cartoonland', 'NA', '98765', 1, 0, '555', '987-6543', 'felix@toons.com');

INSERT INTO `StudentYear` (`studentID`, `yearid`, `isActive`)
VALUES
    (1, 2005, 1),
    (2, 2009, 1),
    (3, 2003, 1),
    (4, 2011, 1),
    (5, 2008, 1),
    (6, 2002, 1),
    (7, 2007, 1),
    (8, 2004, 1),
    (9, 2012, 1),
    (10, 2001, 1),
    (11, 2006, 1),
    (12, 2010, 1),
    (13, 2002, 1),
    (14, 2009, 1),
    (15, 2004, 1),
    (16, 2008, 1),
    (17, 2003, 1),
    (18, 2011, 1),
    (19, 2005, 1),
    (20, 2007, 1),
    (21, 2001, 1),
    (22, 2012, 1),
    (23, 2006, 1),
    (24, 2010, 1),
    (25, 2002, 1),
    (26, 2009, 1),
    (27, 2004, 1),
    (28, 2008, 1),
    (29, 2003, 1),
    (30, 2011, 1),
    (31, 2005, 1),
    (32, 2007, 1),
    (33, 2001, 1),
    (34, 2012, 1),
    (35, 2006, 1),
    (36, 2010, 1),
    (37, 2002, 1),
    (38, 2009, 1),
    (39, 2004, 1),
    (40, 2008, 1),
    (41, 2003, 1),
    (42, 2011, 1),
    (43, 2005, 1),
    (44, 2007, 1),
    (45, 2001, 1),
    (46, 2012, 1),
    (47, 2006, 1),
    (48, 2010, 1),
    (49, 2002, 1),
    (50, 2009, 1);

INSERT INTO `StudentYear` (`studentID`, `yearId`, `isActive`)
VALUES
    (1, 2003, 1),
    (2, 2008, 1),
    (3, 2010, 1),
    (4, 2005, 1),
    (5, 2001, 1),
    (6, 2012, 1),
    (7, 2009, 1),
    (8, 2003, 1),
    (9, 2007, 1),
    (10, 2002, 1),
    (11, 2011, 1),
    (12, 2006, 1),
    (13, 2003, 1),
    (14, 2008, 1),
    (15, 2010, 1),
    (16, 2005, 1),
    (17, 2001, 1),
    (18, 2012, 1),
    (19, 2009, 1),
    (20, 2004, 1),
    (21, 2007, 1),
    (22, 2002, 1),
    (23, 2011, 1),
    (24, 2006, 1),
    (25, 2003, 1),
    (26, 2008, 1),
    (27, 2010, 1),
    (28, 2005, 1),
    (29, 2001, 1),
    (30, 2012, 1),
    (31, 2009, 1),
    (32, 2004, 1),
    (33, 2007, 1),
    (34, 2002, 1),
    (35, 2011, 1),
    (36, 2006, 1),
    (37, 2003, 1),
    (38, 2008, 1),
    (39, 2010, 1),
    (40, 2005, 1),
    (41, 2001, 1),
    (42, 2012, 1),
    (43, 2009, 1),
    (44, 2004, 1),
    (45, 2007, 1),
    (46, 2002, 1),
    (47, 2011, 1),
    (48, 2006, 1),
    (49, 2003, 1),
    (50, 2008, 1);