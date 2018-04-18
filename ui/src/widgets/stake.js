import React, { Component } from 'react';
import {Card, CardActions, CardHeader} from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';
import Dialog from 'material-ui/Dialog';
import TextField from 'material-ui/TextField';
import axios from 'axios';
import SelectField from 'material-ui/SelectField';
import MenuItem from 'material-ui/MenuItem';
import { WithContext as ReactTags } from 'react-tag-input';
import './tags.css'

class Stake extends Component {

  constructor(props) {
    super(props);
    this.state = {
      "dialogOpen": false,
      "dialogTitle": "Deposit Amount",
      "dialogText": "",
      "dialogForm": false,
      "applicationMode": "s",
      "password": "",
      "applicationAuths": [],
      "suggestions": []
    }
  }

  componentDidMount(){
    axios.get('/subauths').then((response) => {
      let auths = response.data
      let suggestions = auths.map((auth) => {
        return {id: auth.name, text:auth.name}
      });
      this.setState({suggestions:suggestions})
    }).catch((error) => {

    })
  }

  openDialog = (title) => {
    if(this.props.account.score <= 0) {
        this.setState({
            dialogOpen: true, 
            dialogTitle: "Pool Registration",
            dialogText: "Deposit 1000 HLC to register for Farming Pool?",
            dialogForm: false
        });
    }
    else {
      this.setState({
        dialogOpen: true,
        dialogTitle: "Edit Application",
        dialogText: "You can edit your application list and mode",
        dialogForm: true,
        applicationMode: this.props.account.application.mode,
        applicationAuths: this.props.account.application.list.map((name) => {return {id:name, text:name}})
      })
    }
  };

  closeDialog = () => {
    this.setState({dialogOpen: false});
  };

  onAmountChange = (e) => {
    this.setState({amount: e.target.value});
  };

  onPasswordChange = (e) => {
    this.setState({password: e.target.value});
  }

  checkPowerStatus = () => {
    this.props.notify('There will be a summary here!', 'success')
  }

  handleApplicationModeChange = (event, index, value) => {
    this.setState({applicationMode: value})
  }

  stakeAction = () => {
    if(!this.state.dialogForm) {
      let data = new FormData();
      data.append('password', this.state.password)
      axios.post('/tx/pool_reg', data).then((response) => {
        let success = response.data.success;
        if(success) {
          this.props.notify(response.data.message, 'success');
        }
        else {
          this.props.notify(response.data.message, 'error');
        }
      })
    }
    else {
      let data = new FormData();
      data.append('mode', this.state.applicationMode)
      data.append('list', this.state.applicationAuths.map(auth => auth.text).join(","))
      data.append('password', this.state.password)
      axios.post('/tx/application', data).then((response) => {
        let success = response.data.success;
        if(success) {
          this.props.notify(response.data.message, 'success');
        }
        else {
          this.props.notify(response.data.message, 'error');
        }
      })
    }

    this.setState({dialogOpen: false});
  }

  handleAuthDelete = (i) => {
    let tags = this.state.applicationAuths
    tags.splice(i, 1)
    this.setState({
      applicationAuths: tags
    });
  }

  handleAuthAddition = (tag) => {
    this.setState({ applicationAuths: [...this.state.applicationAuths, { id: this.state.applicationAuths.length + 1 + "", text: tag.text }] });
  }

  handleAuthDrag = (tag, currPos, newPos) => {
    const applicationAuths = [...this.state.applicationAuths];

    // mutate array
    applicationAuths.splice(currPos, 1);
    applicationAuths.splice(newPos, 0, tag);

    // re-render
    this.setState({ applicationAuths });
  }

  render() {
    let score = 0;
    let applicationMode = 'Single';
    let applicationList = [];
    let assignedJob = "None";
    if(this.props.account !== null){
      score = this.props.account.score;
      applicationMode = this.props.account.application.mode === 's' ? 'Single':'Continuous';
      applicationList = this.props.account.application.list;
      if(this.props.account.assigned_job.auth !== null) {
        assignedJob = "Auth " + this.props.account.assigned_job.auth + " JobId " + this.props.account.assigned_job.job_id;
      }
    }

    const actions = [
      <RaisedButton
        label="Ok"
        primary={true}
        keyboardFocused={true}
        onClick={this.stakeAction}
      />,
    ];

    let form = <div></div>;
    if(this.state.dialogForm) {
        form = <div>
                    <SelectField
                      floatingLabelText="Application Mode"
                      value={this.state.applicationMode}
                      onChange={this.handleApplicationModeChange}
                      autoWidth={true}
                      style={{marginBottom:"32px"}}
                    >
                      <MenuItem value={'s'} primaryText="Single" />
                      <MenuItem value={'c'} primaryText="Continuous" />
                    </SelectField>
                    <ReactTags
                      placeholder={"Add new Authority"}
                      tags={this.state.applicationAuths}
                      suggestions={this.state.suggestions}
                      handleDelete={this.handleAuthDelete}
                      handleAddition={this.handleAuthAddition}
                      handleDrag={this.handleAuthDrag}
                    />
                    <TextField
                        fullWidth={true}
                        floatingLabelText="Password"
                        name="password"
                        type="password"
                        onChange={this.onPasswordChange}
                    />
                </div>;
    } else {
      form = <div>
                <TextField
                    fullWidth={true}
                    floatingLabelText="Password"
                    name="password"
                    type="password"
                    onChange={this.onPasswordChange}
                />
            </div>;
    }

    return (
      <Card style={{width:"100%"}}>
        <CardHeader
          title="Score"
          subtitle={score}
        />
        <CardHeader
          title="Assigned Job"
          subtitle={assignedJob}
        />
        <CardHeader
          title="Application Mode"
          subtitle={applicationMode}
        />
        <CardHeader
          title="Application List"
          subtitle={applicationList.length !== 0 ? applicationList.join(", ") : "Empty"}
        />
        <CardActions align='right'>
          <RaisedButton label="Edit Application" primary={true} onClick={() => {this.openDialog()}} />
        </CardActions>
        <Dialog
          title={this.state.dialogTitle}
          actions={actions}
          modal={false}
          open={this.state.dialogOpen}
          onRequestClose={this.closeDialog}
        >
          {this.state.dialogText}
          {form}
        </Dialog>
      </Card>
    );
  }
}

export default Stake;