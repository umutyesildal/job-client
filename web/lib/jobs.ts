export type Job = {
  company: string;
  title: string;
  location: string;
  link: string;
  postedDate: string;
  remote: string;
  department: string;
};

export type JobsSnapshot = {
  all: Job[];
  daily: Job[];
  updatedAt: string;
};
