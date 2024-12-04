import React, { useEffect, useState } from "react";
import { getMeetingDetails } from "../api";
import { Card, CardContent, Typography, List, ListItem, ListItemText } from "@mui/material";

const MeetingDetails = ({ meetingId }) => {
  const [meeting, setMeeting] = useState(null);
  const [feedback, setFeedback] = useState([]);

  useEffect(() => {
    const fetchMeetingDetails = async () => {
      try {
        const response = await getMeetingDetails(meetingId);
        setMeeting(response.data.meeting);
        setFeedback(response.data.feedback);
      } catch (error) {
        console.error("Error fetching meeting details:", error);
      }
    };

    if (meetingId) {
      fetchMeetingDetails();
    }
  }, [meetingId]);

  if (!meeting) {
    return (
      <Typography variant="body1" style={{ marginTop: "20px" }}>
        Select a meeting to view details.
      </Typography>
    );
  }

  return (
    <Card style={{ marginTop: "20px" }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Meeting Details
        </Typography>
        <Typography>
          <strong>Title:</strong> {meeting[1]}
        </Typography>
        <Typography>
          <strong>Date:</strong> {meeting[2]}
        </Typography>
        <Typography>
          <strong>Time:</strong> {meeting[3]}
        </Typography>
        <Typography>
          <strong>Attendees:</strong> {meeting[4]}
        </Typography>
        <Typography>
          <strong>Status:</strong> {meeting[5]}
        </Typography>

        <Typography variant="h6" style={{ marginTop: "20px" }}>
          Feedback
        </Typography>
        {feedback.length > 0 ? (
          <List>
            {feedback.map((fb) => (
              <ListItem key={fb[0]}>
                <ListItemText
                  primary={`Rating: ${fb[2]}`}
                  secondary={fb[3] || "No comments provided"}
                />
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography>No feedback available for this meeting.</Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default MeetingDetails;
