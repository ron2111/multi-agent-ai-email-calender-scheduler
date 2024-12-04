import React from "react";
import MeetingList from "./components/MeetingList";
import MeetingDetails from "./components/MeetingDetails";
import Header from "./components/Header";
import { ThemeProvider, createTheme, CssBaseline } from "@mui/material";
import { Grid, Container } from "@mui/material";

const theme = createTheme();

function App() {
  const [selectedMeeting, setSelectedMeeting] = React.useState(null);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Header />
      <Container>
        <Grid container spacing={4}>
          <Grid item xs={12} md={6}>
            <MeetingList onSelectMeeting={setSelectedMeeting} />
          </Grid>
          <Grid item xs={12} md={6}>
            <MeetingDetails meetingId={selectedMeeting} />
          </Grid>
        </Grid>
      </Container>
    </ThemeProvider>
  );
}

export default App;
