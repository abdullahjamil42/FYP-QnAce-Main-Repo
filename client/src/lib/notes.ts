import aiMlDataAnalytics from "./notes/ai-ml-data-analytics.md";
import cloudComputing from "./notes/cloud-computing.md";
import cybersecurity from "./notes/cybersecurity.md";
import softwareEngineering from "./notes/software-engineering.md";
import webDevelopment from "./notes/web-development.md";
import dataStructuresAlgorithms from "./notes/data-structures-algorithms.md";
import databases from "./notes/databases.md";
import operatingSystems from "./notes/operating-systems.md";
import problemSolving from "./notes/problem-solving.md";
import programming from "./notes/programming.md";
import computerNetworks from "./notes/computer-networks-cloud-computing.md";

const notesMap: Record<string, string> = {
  "AI / Machine Learning and Data Analytics": aiMlDataAnalytics,
  "Cloud Computing": cloudComputing,
  Cybersecurity: cybersecurity,
  "Software Engineering": softwareEngineering,
  "Web Development": webDevelopment,
  "Data Structures and Algorithms": dataStructuresAlgorithms,
  Databases: databases,
  "Operating Systems": operatingSystems,
  "Problem Solving and Analytical Skills": problemSolving,
  "Programming (C++/Java/Python)": programming,
  "Computer Networks and Cloud Computing": computerNetworks,
};

export function getNoteForTopic(topic: string): string | null {
  return notesMap[topic] || null;
}
