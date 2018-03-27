import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import {Card, CardActions, CardHeader, CardText, CardTitle} from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';
import Dialog from 'material-ui/Dialog';
import TextField from 'material-ui/TextField';
import axios from 'axios';
import {
  Table,
  TableBody,
  TableHeader,
  TableHeaderColumn,
  TableRow,
  TableRowColumn,
} from 'material-ui/Table';
import Avatar from 'material-ui/Avatar';
import FontIcon from 'material-ui/FontIcon';
import {yellow800} from 'material-ui/styles/colors';

class Stake extends Component {

  constructor(props) {
    super(props);
    this.state = {
      "dialogOpen": false,
      "dialogTitle": "Deposit Amount",
      "dialogText": "",
      "dialogForm": false
    }
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
        dialogForm: true
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

  stakeAction = () => {
    if(!this.state.dialogForm) {
      axios.post('/tx/pool_reg').then((response) => {
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
      let password = this.state.password;
      let amount = this.state.amount;
      let data = new FormData();
      let address = "";
      if(this.state.dialogTitle === 'Deposit') {
        address = "/deposit";  
      }
      else{
        address = "/withdraw";
      }
      
      data.append('amount', amount);
      data.append('password', password);
  
      axios.post(address, data).then((response) => {
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

  render() {
    let score = 0;
    let applicationMode = 'Single';
    let applicationList = [];
    let name = "";
    let assignedJob = "None";
    if(this.props.account !== null){
      score = this.props.account.score;
      applicationMode = this.props.account.application.mode == 's' ? 'Single':'Continous';
      applicationList = this.props.account.application.list;
      name = this.props.wallet.name;
      if(this.props.account.assigned_job.auth !== null) {
        assignedJob = "Auth " + this.props.wallet.assigned_job.auth + " JobId " + this.props.wallet.assigned_job.job_id;
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
                    <TextField
                        fullWidth={true}
                        floatingLabelText="Amount"
                        name="amount"
                        type="text"
                        onChange={this.onAmountChange}
                    />
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
          subtitle={applicationList.length != 0 ? applicationList.join(", ") : "Empty"}
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