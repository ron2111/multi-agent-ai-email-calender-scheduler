import React, { useEffect, useState } from "react";
import { getMeetings } from "../api";
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography } from "@mui/material";

const MeetingList = ({ onSelectMeeting }) => {
  const [meetings, setMeetings] = useState([]);

  useEffect(() => {
    const fetchMeetings = async () => {
      try {
        const response = await getMeetings();
        setMeetings(response.data.meetings);
      } catch (error) {
        console.error("Error fetching meetings:", error);
      }
    };

    fetchMeetings();
  }, []);

  return (
    <div>
      <Typography variant="h6" style={{ marginBottom: "10px" }}>
        Meetings List
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Title</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Time</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {meetings.map((meeting) => (
              <TableRow
                key={meeting[0]}
                style={{ cursor: "pointer" }}
                onClick={() => onSelectMeeting(meeting[0])}
              >
                <TableCell>{meeting[0]}</TableCell>
                <TableCell>{meeting[1]}</TableCell>
                <TableCell>{meeting[2]}</TableCell>
                <TableCell>{meeting[3]}</TableCell>
                <TableCell>{meeting[5]}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  );
};

export default MeetingList;
