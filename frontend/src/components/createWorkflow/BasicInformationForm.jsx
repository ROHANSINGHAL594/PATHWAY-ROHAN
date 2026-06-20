import {
  Box,
  Typography,
  TextField,
  Autocomplete,
  Chip,
  Avatar,
  ListItemAvatar,
  MenuItem,
  Select,
  FormControl,
  IconButton,
  useTheme,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import CloseIcon from "@mui/icons-material/Close";
import aiIcon from "../../assets/ai_icon.svg";
import { fetchAllUsers } from "../../utils/developerDashboard.api";

const BasicInformationForm = ({ formData, onInputChange, onFileChange, onMembersChange, allUsers, setAllUsers, loadingUsers, setLoadingUsers }) => {

  // Load users when Autocomplete dropdown is opened
  const handleOpenAutocomplete = async () => {
    // Only fetch if we haven't loaded users yet
    if (allUsers.length === 0 && !loadingUsers) {
      setLoadingUsers(true);
      try {
        const users = await fetchAllUsers();
        // Handle both array response and object with data property
        const usersArray = Array.isArray(users) ? users : users?.data || [];
        console.log("Loaded users:", usersArray); // Debug log
        console.log("Setting allUsers state with:", usersArray.length, "users");
        console.log("Users array:", JSON.stringify(usersArray, null, 2));
        setAllUsers(usersArray);
      } catch (error) {
        console.error("Error loading users:", error);
        setAllUsers([]);
      } finally {
        setLoadingUsers(false);
      }
    } else {
      console.log("Users already loaded:", allUsers.length);
      console.log("Current allUsers:", allUsers);
    }
  };
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      {/* Name Field */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        <Typography
          component="label"
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            color: "text.primary",
          }}
        >
          Name
        </Typography>
        <TextField
          fullWidth
          placeholder="Name"
          value={formData.name}
          onChange={onInputChange("name")}
          variant="filled"
          InputProps={{
            disableUnderline: true,
          }}
          sx={{
            "& .MuiFilledInput-root": {
              bgcolor: "background.elevation2",
              borderRadius: 2,
              "&:hover": { bgcolor: "background.elevation1" },
              "&.Mui-focused": {
                bgcolor: "background.elevation1",
                boxShadow: (theme) =>
                  `0 0 0 2px ${theme.palette.primary.light}`,
              },
            },
            "& .MuiFilledInput-input": {
              py: 1.5,
              px: 2,
              fontSize: "0.875rem",
              "&::placeholder": { color: "text.secondary", opacity: 1 },
            },
          }}
        />
      </Box>

      {/* Document Upload Field */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        <Typography
          component="label"
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            color: "text.primary",
          }}
        >
          Upload Document
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Box
            component="label"
            htmlFor="document-upload"
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              bgcolor: "background.elevation2",
              borderRadius: 2,
              py: 1.5,
              px: 2,
              cursor: "pointer",
              border: "1px dashed",
              borderColor: "divider",
              transition: "all 0.2s ease",
              flex: 1,
              maxWidth: "70%",
              "&:hover": {
                bgcolor: "background.elevation1",
                borderColor: "primary.main",
              },
            }}
          >
            <input
              id="document-upload"
              type="file"
              hidden
              onChange={onFileChange}
              accept=".pdf,.doc,.docx,.txt"
            />
            <UploadFileIcon
              sx={{
                color: formData.document ? "primary.main" : "text.secondary",
                fontSize: 20,
              }}
            />
            <Typography
              variant="body2"
              sx={{
                color: formData.document ? "text.primary" : "text.secondary",
                flex: 1,
              }}
            >
              {formData.document
                ? formData.document.name
                : "Click to upload from device"}
            </Typography>
            {formData.document && (
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  onFileChange({ target: { files: [] } });
                  const fileInput = document.getElementById("document-upload");
                  if (fileInput) {
                    fileInput.value = "";
                  }
                }}
                sx={{
                  color: "text.secondary",
                  "&:hover": { color: "error.main" },
                }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            )}
          </Box>
          <Box
            component="img"
            src={aiIcon}
            alt="AI Icon"
            sx={{
              width: 38,
              height: 38,
              flexShrink: 0,
            }}
          />
        </Box>
      </Box>

      {/* Description Field */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        <Typography
          component="label"
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            color: "text.primary",
          }}
        >
          Description
        </Typography>
        <TextField
          fullWidth
          placeholder="Description"
          value={formData.description}
          onChange={onInputChange("description")}
          variant="filled"
          multiline
          rows={4}
          InputProps={{
            disableUnderline: true,
          }}
          sx={{
            "& .MuiFilledInput-root": {
              bgcolor: "background.elevation2",
              borderRadius: 2,
              alignItems: "flex-start",
              "&:hover": { bgcolor: "background.elevation1" },
              "&.Mui-focused": {
                bgcolor: "background.elevation1",
                boxShadow: (theme) =>
                  `0 0 0 2px ${theme.palette.primary.light}`,
              },
            },
            "& .MuiFilledInput-input": {
              py: 1.5,
              px: 2,
              fontSize: "0.875rem",
              "&::placeholder": { color: "text.secondary", opacity: 1 },
            },
          }}
        />
      </Box>

      {/* Members Field */}
      {/* <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        <Typography
          component="label"
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            color: "text.primary",
          }}
        >
          Members
        </Typography>
        <FormControl fullWidth variant="filled">
          <Select
            value={formData.members}
            onChange={onInputChange("members")}
            displayEmpty
            disableUnderline
            IconComponent={KeyboardArrowDownIcon}
            sx={{
              bgcolor: "background.elevation2",
              borderRadius: 2,
              "&:hover": { bgcolor: "background.elevation1" },
              "&.Mui-focused": {
                bgcolor: "background.elevation1",
                boxShadow: (theme) => `0 0 0 2px ${theme.palette.primary.light}`,
              },
              "& .MuiSelect-select": {
                py: 1.5,
                px: 2,
                fontSize: "0.875rem",
                color: formData.members ? "text.primary" : "text.secondary",
              },
              "& .MuiSelect-icon": {
                color: "text.secondary",
                right: 12,
              },
            }}
            MenuProps={{
              PaperProps: {
                sx: { zIndex: 10001 },
              },
            }}
          >
            <MenuItem value="" disabled>
              Select members
            </MenuItem>
            <MenuItem value="admin">Admin</MenuItem>
            <MenuItem value="developer">Developer</MenuItem>
            <MenuItem value="viewer">Viewer</MenuItem>
          </Select>
        </FormControl>
      </Box> */}

      {/* Members Field */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        <Typography
          component="label"
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            color: "text.primary",
          }}
        >
          Members
        </Typography>
        <Autocomplete
          multiple
          options={allUsers || []}
          value={formData.selectedMembers || []}
          onOpen={(event) => {
            console.log("Autocomplete opened, allUsers:", allUsers.length);
            handleOpenAutocomplete();
          }}
          openOnFocus
          disablePortal={false}
          freeSolo={false}
          disableCloseOnSelect
          clearOnBlur={false}
          onChange={(event, newValue) => {
            console.log("Selected members:", newValue);
            if (onMembersChange) {
              onMembersChange(newValue);
            }
          }}
          onInputChange={(event, value, reason) => {
            console.log("Input changed:", value, reason);
            console.log("Current allUsers:", allUsers);
          }}
          getOptionLabel={(option) => {
            if (!option || typeof option !== "object") return "";
            const name = option.full_name || option.name || `User ${option.id}`;
            const email = option.email || "";
            return email ? `${name} <${email}>` : name;
          }}
          isOptionEqualToValue={(option, value) => {
            if (!option || !value) return false;
            return String(option.id) === String(value.id);
          }}
          filterOptions={(options, params) => {
            console.log("Filtering options:", options.length, "options");
            const searchText = params.inputValue
              ? params.inputValue.toLowerCase().trim()
              : "";
            if (!searchText) {
              // Show all options when no search text
              console.log(
                "No search text, returning all",
                options.length,
                "options"
              );
              return options;
            }
            // Filter options based on search text
            const filtered = options.filter((option) => {
              if (!option) return false;
              const name = (
                option.full_name ||
                option.name ||
                ""
              ).toLowerCase();
              const email = (option.email || "").toLowerCase();
              return name.includes(searchText) || email.includes(searchText);
            });
            console.log("Filtered to", filtered.length, "options");
            return filtered;
          }}
          loading={loadingUsers}
          noOptionsText={loadingUsers ? "Loading users..." : "No users found"}
          renderInput={(params) => {
            const hasSelectedMembers = (formData.selectedMembers || []).length > 0;
            return (
            <TextField
              {...params}
              variant="filled"
                placeholder={hasSelectedMembers ? "" : "Add Viewers"}
              InputProps={{
                ...params.InputProps,
                disableUnderline: true,
              }}
              sx={{
                "& .MuiFilledInput-root": {
                  bgcolor: "background.elevation2",
                  borderRadius: 2,
                  minHeight: "56px",
                    display: "flex",
                    alignItems: "center",
                    padding: "4px 8px",
                  "&:hover": { bgcolor: "background.elevation1" },
                  "&.Mui-focused": {
                    bgcolor: "background.elevation1",
                    boxShadow: (theme) =>
                      `0 0 0 2px ${theme.palette.primary.light}`,
                  },
                },
                "& .MuiFilledInput-input": {
                  py: 1.5,
                  px: 2,
                  fontSize: "0.875rem",
                    height: "auto",
                    display: "flex",
                    alignItems: "center",
                  },
                  "& .MuiInputBase-input": {
                    display: "flex",
                    alignItems: "center",
                    height: "auto",
                  },
                  "& .MuiAutocomplete-inputRoot": {
                    display: "flex",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "4px",
                  },
                  "& .MuiAutocomplete-tag": {
                    margin: 0,
                    height: "28px",
                    display: "inline-flex",
                    alignItems: "center",
                  },
                  "& .MuiAutocomplete-endAdornment": {
                    display: "flex",
                    alignItems: "center",
                    top: "50%",
                    transform: "translateY(-50%)",
                    right: "8px",
                },
              }}
            />
            );
          }}
          renderTags={(value, getTagProps) =>
            value.map((option, index) => {
              const { key, ...tagProps } = getTagProps({ index });
              const name =
                option.full_name || option.name || `User ${option.id}`;
              return (
                <Chip
                  key={key}
                  label={name}
                  {...tagProps}
                  sx={{
                    bgcolor: "action.hover",
                    color: "text.primary",
                    height: "28px",
                    border: "1px solid",
                    borderColor: "text.primary",
                    "& .MuiChip-label": {
                      px: 1.5,
                      fontSize: "0.875rem",
                      fontWeight: 400,
                      display: "flex",
                      alignItems: "center",
                    },
                    "& .MuiChip-deleteIcon": {
                      color: "text.primary",
                      fontSize: "18px",
                      marginRight: "4px",
                      "&:hover": {
                        color: "text.primary",
                        opacity: 0.7,
                      },
                    },
                  }}
                />
              );
            })
          }
          renderOption={(props, option) => {
            if (!option) return null;
            const name = option.full_name || option.name || `User ${option.id}`;
            const email = option.email || "";
            const avatarUrl = `https://avatar.iran.liara.run/public/boy?username=${encodeURIComponent(
              name || option.id || `user${option.id}`
            )}&size=40`;

            // Extract key from props if it exists
            const { key, ...otherProps } = props;

            return (
              <li {...otherProps} key={key || option.id}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    py: 1.5,
                    px: 2,
                    cursor: "pointer",
                    width: "100%",
                    "&:hover": {
                      bgcolor: "action.hover",
                    },
                  }}
                >
                  <Avatar
                    src={avatarUrl}
                    alt={name}
                    sx={{
                      width: 40,
                      height: 40,
                      flexShrink: 0,
                    }}
                  >
                    {name.charAt(0).toUpperCase()}
                  </Avatar>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      sx={{
                        fontSize: "0.875rem",
                        fontWeight: 500,
                        color: "text.primary",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {name}
                    </Typography>
                    <Typography
                      sx={{
                        fontSize: "0.75rem",
                        color: "text.secondary",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {email}
                    </Typography>
                  </Box>
                </Box>
              </li>
            );
          }}
          getOptionKey={(option) => String(option.id)}
          slotProps={{
            paper: {
              sx: {
                zIndex: 10005,
                maxHeight: 400,
                boxShadow: 3,
                mt: 1,
                "& .MuiAutocomplete-listbox": {
                  padding: 0,
                  maxHeight: "400px",
                  overflowY: "auto",
                  overflowX: "hidden",
                  "&::-webkit-scrollbar": {
                    width: "8px",
                  },
                  "&::-webkit-scrollbar-track": {
                    background: "transparent",
                  },
                  "&::-webkit-scrollbar-thumb": {
                    background: "rgba(0, 0, 0, 0.2)",
                    borderRadius: "4px",
                    "&:hover": {
                      background: "rgba(0, 0, 0, 0.3)",
                    },
                  },
                  "& .MuiAutocomplete-option": {
                    padding: 0,
                  },
                },
              },
            },
            popper: {
              placement: "bottom-start",
              sx: { zIndex: 10005 },
              modifiers: [
                {
                  name: "offset",
                  options: {
                    offset: [0, 4],
                  },
                },
              ],
            },
          }}
          ListboxProps={{
            style: {
              maxHeight: "400px",
              overflowY: "auto",
              overflowX: "hidden",
            },
          }}
        />
      </Box>
    </Box>
  );
};

export default BasicInformationForm;
