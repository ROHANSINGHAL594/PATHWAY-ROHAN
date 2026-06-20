import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  Box,
  Typography,
  IconButton,
  TextField,
  InputAdornment,
  Button,
  Menu,
  MenuItem,
  useTheme,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import SearchIcon from "@mui/icons-material/Search";
import FilterListIcon from "@mui/icons-material/FilterList";
import CheckIcon from "@mui/icons-material/Check";
import aiIcon from "../../assets/ai_icon.svg";
import downtimeIcon from "../../assets/downtime.svg";
import errorRateIcon from "../../assets/error_rate.svg";
import latencyIcon from "../../assets/latency.svg";

// Template data
const templates = {
  blank: [
    {
      id: "blank",
      name: "Create New AI Workflow",
      image: aiIcon,
      bgColor: "#424242",
    },
  ],
  sla: [
    {
      id: "downtime",
      name: "Downtime",
      image: downtimeIcon,
      bgColor: "#424242",
    },
    {
      id: "error-rate",
      name: "Error Rate",
      image: errorRateIcon,
      bgColor: "#424242",
    },
    {
      id: "latency",
      name: "Latency",
      image: latencyIcon,
      bgColor: "#424242",
    },
  ],
};

const NewProjectModal = ({ open, onClose, onSelectTemplate }) => {
  const theme = useTheme();
  const [searchQuery, setSearchQuery] = useState("");
  const [filterAnchor, setFilterAnchor] = useState(null);
  const [selectedFilter, setSelectedFilter] = useState("all");

  const handleTemplateClick = (template) => {
    if (onSelectTemplate) {
      onSelectTemplate(template);
    }
    onClose();
  };

  const handleFilterClick = (event) => {
    setFilterAnchor(event.currentTarget);
  };

  const handleFilterClose = () => {
    setFilterAnchor(null);
  };

  const handleFilterSelect = (filter) => {
    setSelectedFilter(filter);
    setFilterAnchor(null);
  };

  const filterTemplates = (templateList) => {
    if (!searchQuery) return templateList;
    return templateList.filter((t) =>
      t.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  };

  // Get filtered sections based on selected filter
  const getFilteredSections = () => {
    if (selectedFilter === "all") {
      return Object.entries(templates);
    }
    return Object.entries(templates).filter(([key]) => key === selectedFilter);
  };

  const filteredSections = getFilteredSections();

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: "16px",
          maxHeight: "85vh",
          boxShadow: theme.shadows[20],
        },
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 5,
          py: 2.5,
          bgcolor: "background.paper",
        }}
      >
        <Typography
          sx={{
            fontSize: "21px",
            fontWeight: 700,
            lineHeight: "32px",
            color: "text.primary",
          }}
        >
          New Project
        </Typography>
        <IconButton
          onClick={onClose}
          size="small"
          sx={{
            color: "text.secondary",
            width: 32,
            height: 32,
            "&:hover": { bgcolor: "action.hover" },
          }}
        >
          <CloseIcon sx={{ fontSize: "20px" }} />
        </IconButton>
      </Box>

      <DialogContent
        sx={{
          p: 0,
          display: "flex",
          flexDirection: "column",
          gap: 5,
        }}
      >
        {/* Search and Filter */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: 5,
            py: 2.5,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <TextField
            placeholder="Search"
            variant="filled"
            size="small"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            sx={{
              width: 355,
              "& .MuiFilledInput-root": {
                bgcolor: "background.elevation2",
                borderRadius: 2,
                height: 36,
                minHeight: 36,
                "&:hover": { bgcolor: "background.elevation2" },
                "&.Mui-focused": { bgcolor: "background.elevation2" },
              },
              "& .MuiFilledInput-input": {
                px: 2,
                py: 0,
                fontSize: "14px",
                fontWeight: 400,
                lineHeight: "22px",
                "&::placeholder": {
                  color: "text.secondary",
                  opacity: 1,
                },
              },
              "& .MuiInputAdornment-root": {
                mt: "0 !important",
                mr: 1,
              },
            }}
            InputProps={{
              disableUnderline: true,
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon
                    sx={{ color: "text.secondary", fontSize: "20px" }}
                  />
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="text"
            startIcon={<FilterListIcon sx={{ fontSize: "20px" }} />}
            onClick={handleFilterClick}
            sx={{
              color: "text.primary",
              textTransform: "none",
              fontSize: "14px",
              fontWeight: 600,
              lineHeight: "18px",
              px: 1,
              py: 1.625,
              minHeight: 36,
              borderRadius: 2,
              "&:hover": { bgcolor: "action.hover" },
            }}
          >
            Filter
          </Button>
          <Menu
            anchorEl={filterAnchor}
            open={Boolean(filterAnchor)}
            onClose={handleFilterClose}
            anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            transformOrigin={{ vertical: "top", horizontal: "right" }}
          >
            <MenuItem onClick={() => handleFilterSelect("all")}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  width: "100%",
                }}
              >
                {selectedFilter === "all" && (
                  <CheckIcon sx={{ fontSize: 20 }} />
                )}
                <Typography sx={{ ml: selectedFilter === "all" ? 0 : 3.5 }}>
                  All
                </Typography>
              </Box>
            </MenuItem>
            {Object.keys(templates).map((key) => (
              <MenuItem key={key} onClick={() => handleFilterSelect(key)}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    width: "100%",
                  }}
                >
                  {selectedFilter === key && (
                    <CheckIcon sx={{ fontSize: 20 }} />
                  )}
                  <Typography sx={{ ml: selectedFilter === key ? 0 : 3.5 }}>
                    {key.toUpperCase()}
                  </Typography>
                </Box>
              </MenuItem>
            ))}
          </Menu>
        </Box>

        {/* Divider */}
        <Box sx={{ width: "100%", height: 1, bgcolor: "divider", m: 0 }} />

        {/* Dynamic Template Sections */}
        {filteredSections.map(([sectionKey, sectionTemplates], index) => (
          <React.Fragment key={sectionKey}>
            <Box
              sx={{
                px: 5,
                mt: -5,
                display: "flex",
                flexDirection: "column",
                gap: 3,
              }}
            >
              {/* Section Title - only show if not "blank" */}
              {sectionKey !== "blank" && (
                <Typography
                  sx={{
                    fontSize: "24px",
                    fontWeight: 500,
                    lineHeight: "36px",
                    color: "text.primary",
                    m: 0,
                  }}
                >
                  {sectionKey.toUpperCase()}
                </Typography>
              )}

              {/* Template Cards */}
              <Box 
                sx={{ 
                  display: "flex", 
                  gap: sectionKey === "sla" || sectionKey === "blank" ? 2 : 3, 
                  flexWrap: "wrap",
                }}
              >
                {filterTemplates(sectionTemplates).map((template, idx) => (
                  <Box
                    key={`${template.id}-${idx}`}
                    onClick={() => handleTemplateClick(template)}
                    sx={{
                      cursor: "pointer",
                      transition: "transform 0.2s ease",
                      width: sectionKey === "sla" || sectionKey === "blank" ? "calc((100% - 32px) / 3)" : 355,
                      minWidth: sectionKey === "sla" || sectionKey === "blank" ? 240 : 355,
                      flexShrink: 0,
                      display: "flex",
                      flexDirection: "column",
                      borderRadius: 4,
                      overflow: "hidden",
                      "&:hover": { transform: "translateY(-2px)" },
                    }}
                  >
                    <Box
                      sx={{
                        width: "100%",
                        height: sectionKey === "sla" || sectionKey === "blank" ? 140 : 200,
                        borderRadius: 4,
                        overflow: "hidden",
                        position: "relative",
                        flexShrink: 0,
                        backgroundColor: theme.palette.mode === "dark" ? "#424242" : "#e8f4f8",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      {template.image && (
                        <Box
                          component="img"
                          src={template.image}
                          alt={template.name}
                          sx={{
                            maxWidth: sectionKey === "blank" ? "100%" : sectionKey === "sla" ? "60%" : "100%",
                            maxHeight: sectionKey === "blank" ? "100%" : sectionKey === "sla" ? "60%" : "100%",
                            width: sectionKey === "blank" ? "100px" : sectionKey === "sla" ? "auto" : "100%",
                            height: sectionKey === "blank" ? "100px" : sectionKey === "sla" ? "auto" : "100%",
                            objectFit: sectionKey === "blank" || sectionKey === "sla" ? "contain" : "cover",
                            display: "block",
                            filter: sectionKey === "sla" ? "brightness(0)" : "none",
                          }}
                        />
                      )}
                    </Box>
                    <Box
                      sx={{
                        p: 2,
                        display: "flex",
                        flexDirection: "column",
                        gap: 0.5,
                      }}
                    >
                      <Typography
                        sx={{
                          fontSize: "16px",
                          fontWeight: 700,
                          lineHeight: "21px",
                          color: "text.primary",
                        }}
                      >
                        {template.name}
                      </Typography>
                    </Box>
                  </Box>
                ))}
              </Box>
            </Box>

            {/* Divider between sections */}
            {index < filteredSections.length - 1 && (
              <Box
                sx={{ width: "100%", height: 1, bgcolor: "divider", m: 0 }}
              />
            )}
          </React.Fragment>
        ))}
      </DialogContent>
    </Dialog>
  );
};

export default NewProjectModal;
